# Standard library
from datetime import datetime
import os

# Third‑party
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, flash, redirect, url_for, session  

# Local
from claude_client import categorise_with_claude
from models import db, Transaction
from helpers import (
    allowed_file,
    normalise_description,
    guess_category_from_history,
    get_all_category_names,
    build_claude_payload,
    load_uploaded_csv,
    parse_bank_dataframe,
    build_transactions_from_df,
    save_transactions,
)

#git commit test

# Load our secrets from .env file
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment (.env)")

# Create Flask app
app = Flask(__name__)
app.secret_key = "dev"  # or from env

# Tell Flask where our database lives
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
# Turn off a warning we don't need
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Connect our database to Flask
db.init_app(app)

def get_all_routes():
    """
    Helper: returns a list of all routes for display on the home page.
    Each item is a dict with rule, endpoint, and methods.
    """
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        routes.append({
            'endpoint': rule.endpoint,
            'rule': str(rule),
            'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        })
    routes.sort(key=lambda r: r['rule'])
    return routes

# ========================================
# DATABASE CONNECTION TEST (runs on startup)
# ========================================
with app.app_context():
    # This creates a "temporary session" so we can use db
    try:
        # Simple query: "Does the database exist?"
        with db.engine.connect() as connection:
            connection.execute(db.text("SELECT 1"))
        print("✅ Database connection: SUCCESS!")
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
        exit(1)  # Stop the app if database fails

# ========================================
# WEB ROUTES (these are like web pages)
# ========================================

@app.route("/")
def home():
    """
    Home page: shows main navigation links and some quick stats.
    """
    all_routes = get_all_routes()

    total_tx = Transaction.query.count()
    uncategorised_tx = Transaction.query.filter(
        Transaction.category.is_(None)
    ).count()

    return render_template(
        "home.html",
        routes=all_routes,
        total_tx=total_tx,
        uncategorised_tx=uncategorised_tx,
    )

@app.route('/test-db')
def test_db():
    """TEST ROUTE: Creates + reads transactions from database"""
    with app.app_context():  # Needed for database operations
        
        # Step 1: Create a test transaction
        test_tx = Transaction(
            date=datetime(2026, 2, 12),     # Date of transaction
            amount=45.99,                   # How much
            description="SAINSBURYS UK",    # What they bought
            account="AMEX"                  # Which card
        )
        
        # Step 2: Save it to database
        db.session.add(test_tx)         # Add to "pending" list
        db.session.commit()             # Actually save to database
        
        # Step 3: Read all transactions back
        transactions = Transaction.query.all()
        
        # Step 4: Convert to JSON for web browser
        return jsonify({
            'message': 'Database test successful!',
            'transactions': [{
                'id': t.id,
                'description': t.description,
                'amount': t.amount,
                'account': t.account
            } for t in transactions]  # List comprehension = Python magic
        })
    
@app.route("/upload-csv", methods=["GET", "POST"])
def upload_csv():
    """
    - GET  -> show the HTML form so the user can choose a CSV file
    - POST -> receive the uploaded file, parse it, and store transactions
              in an all-or-nothing way (one bad row = nothing saved).
    """
    if request.method == "GET":
        return render_template("upload.html")

    try:
        # 1) Load CSV from the request
        df = load_uploaded_csv(request)

        # 2) Normalise to our standard columns using the correct bank parser
        standard_df = parse_bank_dataframe(df, request.form.get("bank"))

        # 3) Build Transaction objects (including guess_category_from_history)
        created_transactions = build_transactions_from_df(standard_df)

        # 4) Save all or none
        save_transactions(created_transactions)

        # Remember which transactions we just created so we can review them
        last_ids = [tx.id for tx in created_transactions]
        session["last_upload_ids"] = last_ids

    except ValueError as e:
        # “Expected” user errors (bad file, bad bank, bad row, etc.)
        return render_template("upload.html", message=str(e))
    except Exception as e:
        # Unexpected errors
        return render_template("upload.html", message=f"Error processing CSV: {e}")

    message = f"Successfully imported {len(created_transactions)} transactions."
    flash(message)
    return redirect(url_for("review_last_upload"))

@app.route("/review-last-upload", methods=["GET"])
def review_last_upload():
    """
    Show the transactions from the most recent upload,
    """

    last_ids = session.get("last_upload_ids")

    if not last_ids:
        flash("No recent upload to review.")
        return redirect(url_for("home"))
    
    # Fetch those transactions from the DB, newest first by date
    transactions = (
        Transaction.query
        .filter(Transaction.id.in_(last_ids))
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .all()
    )

    if not transactions:
        flash("No transactions found for the last upload.")
        return redirect(url_for("home"))
    
    # all possible category names for dropdowns
    category_names = get_all_category_names()

    return render_template(
        "review_last_upload.html",
        transactions=transactions,
        category_names=category_names
    )
    
@app.route("/update-categories", methods=["POST"])
def update_categories():
    """
    Update categories for the transactions in the last upload.
    Optionally send remaining uncategorised ones to Claude.
    """

    last_ids = session.get("last_upload_ids")
    if not last_ids:
        flash("No recent upload to update.")
        return redirect(url_for("upload_csv"))

    # Fetch the transactions again
    transactions = Transaction.query.filter(
        Transaction.id.in_(last_ids)
    ).all()

    # 1) Apply user-selected categories
    for tx in transactions:
        field_name = f"category_{tx.id}"
        new_cat = request.form.get(field_name) or None  # empty string -> None
        tx.category = new_cat

    db.session.commit()

    action = request.form.get("action")
    

    print("DEBUG action =", action) #DEBUG

    if action == "send_to_claude":
        # 2) Build payload for uncategorised ones
        uncats = [t for t in transactions if t.category is None]
        if not uncats:
            flash("No uncategorised transactions to send to Claude.")
            return redirect(url_for("review_last_upload"))

        txs = []
        for t in uncats:
            txs.append(
                {
                    "id": t.id,
                    "date": t.date.isoformat() if t.date else None,
                    "amount": t.amount,
                    "description": t.description,
                    "account": t.account,
                }
            )

        category_names = get_all_category_names()
        categories = categorise_with_claude(txs, category_names)

        updated = 0
        for t in uncats:
            if t.id in categories:
                t.category = categories[t.id]
                updated += 1

        db.session.commit()
        flash(f"Claude categorised {updated} transactions.")

    if action == "reset_to_uncategorised":
        # Set all categories to None for these transactions
        for tx in transactions:
            tx.category = None
        db.session.commit()
        flash("All categories reset to Uncategorised.")
        return redirect(url_for("review_last_upload"))    

    else:
        flash("Categories updated.")

    return redirect(url_for("review_last_upload"))

@app.route('/transactions')
def list_transactions():
    """
    HTML view: shows all transactions in a table (newest first).
    """
    # Query all transactions, newest first
    all_tx = Transaction.query.order_by(Transaction.date.desc()).all()

    # Render an HTML template and pass the transactions to it
    return render_template('transactions.html', transactions=all_tx)

@app.route('/uncategorised')
def uncategorised_transactions():
    """
    Returns all transactions that are not yet categorised.
    This is what we will send to Claude
    """

    uncats = Transaction.query.filter(
        Transaction.category.s_(None)
    ).order_by(Transaction.date.desc()).all()

    result = []
    for t in uncats:
        result.append({
            'id': t.id,
            'date': t.date.isoformat() if t.date else None,
            'amount': t.amount,
            'description': t.description, 
            'account': t.account,
            'category': t.category,
        })

    return jsonify(result)
    
@app.route('/uncategorised-view')
def uncategorised_view():
    """
    HTML page showing uncategorised transactions in a table.
    Good for visually checking what will be sent to Claude.
    """
    uncats = Transaction.query.filter(Transaction.category == None).order_by(
        Transaction.date.desc()
    ).all()

    return render_template('uncategorised.html', transactions=uncats)    

@app.route("/categorise-batch")
def categorise_batch():
    print("DEBUG: /categorise-batch called") #DEBUG

    # 1) Get uncategorised transactions using SQLAlchemy
    uncats = Transaction.query.filter(
        Transaction.category.is_(None)
    ).order_by(Transaction.date.desc()).all()

    print(f"DEBUG: found {len(uncats)} uncategorised transactions") #DEBUG

    if not uncats:
        flash("No uncategorised transactions to categorise.")
        return redirect(url_for("home"))

    # 2) Build list of dicts for Claude
    txs = build_claude_payload(uncats)

    # 3) Call Claude
    category_names = get_all_category_names()
    categories = categorise_with_claude(txs, category_names)
    print("DEBUG: categories from Claude:", categories) #DEBUG

    # 4) Write categories back to DB (still SQLAlchemy)
    updated = 0
    for tx in uncats:
        if tx.id in categories:
            tx.category = categories[tx.id]
            updated += 1

    db.session.commit()
    print(f"DEBUG: updated {updated} rows in DB") #DEBUG
    flash(f"Successfully categorised {updated} transactions.")
    return redirect(url_for("home"))

# ========================================
# START THE APP
# ========================================
if __name__ == '__main__':
    # CREATE DATABASE TABLES (only needed first time)
    with app.app_context():
        db.create_all()  # Makes "transactions" table
        print("✅ Database tables created!")
    
    # START WEB SERVER
    app.run(debug=True)
