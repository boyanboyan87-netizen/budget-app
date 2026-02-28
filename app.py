# Standard library
from datetime import timedelta, datetime
import os

# Third‑party
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, flash, redirect, url_for, session
from flask_login import LoginManager, login_required, current_user
from plaid_client import create_link_token, exchange_public_token, sync_transactions

# Local
from claude_client import categorise_with_claude
from models import db, Transaction, User, PlaidItem, PlaidAccount
from auth import auth_bp, init_oauth

from helpers import (
    get_all_category_names,
    build_claude_payload,
    load_uploaded_csv,
    parse_bank_dataframe,
    build_transactions_from_df,
    build_transactions_from_plaid,
    save_transactions,
)

load_dotenv()

login_manager = LoginManager()


def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__)

    # Apply overrides first so tests can inject DB URL + SECRET_KEY before checks
    if config_override:
        app.config.update(config_override)

    # Resolve secrets from config (tests inject directly) or env
    secret_key = app.config.get('SECRET_KEY') or os.getenv("SECRET_KEY")
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI') or os.getenv("DATABASE_URL")

    if not app.config.get('TESTING'):
        if not secret_key:
            raise RuntimeError("SECRET_KEY is not set in the environment (.env)")
        if not db_url:
            raise RuntimeError("DATABASE_URL is not set in the environment (.env)")

    app.secret_key = secret_key or "test-secret"
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///:memory:"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Connection pool — skip for SQLite (used in tests)
    if not app.config.get('TESTING'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 20,
            'max_overflow': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'pool_timeout': 30,
        }

    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') != 'development'

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'landing'
    login_manager.login_message = 'Please log in to access this page'

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return User.query.get(int(user_id))

    init_oauth(app)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        if not app.config.get('TESTING'):
            try:
                with db.engine.connect() as connection:
                    connection.execute(db.text("SELECT 1"))
                print("✅ Database connection: SUCCESS!")
            except Exception as e:
                print(f"❌ Database connection: FAILED - {e}")
                exit(1)

    # ========================================
    # HELPER
    # ========================================

    def get_all_routes() -> list[dict]:
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
    # WEB ROUTES
    # ========================================

    @app.route("/")
    def landing():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        return render_template("landing.html")


    @app.route("/dashboard")
    @login_required
    def home():
        """
        Home page: shows main navigation links and some quick stats.
        """
        all_routes = get_all_routes()

        total_tx = Transaction.query.for_current_user().count()
        uncategorised_tx = Transaction.query.for_current_user().filter(
            Transaction.category_id.is_(None)
        ).count()

        return render_template(
            "home.html",
            routes=all_routes,
            total_tx=total_tx,
            uncategorised_tx=uncategorised_tx,
        )

    @app.route('/db-info')
    def db_info():
        """Show which database we're connected to"""
        return {
            'database_url': 'PostgreSQL on Neon',  # Don't expose credentials
            'dialect': db.engine.dialect.name,
            'driver': db.engine.driver,
        }

    @app.route("/upload-csv", methods=["GET", "POST"])
    @login_required
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
            created_transactions = build_transactions_from_df(standard_df, current_user.id)

            # 4) Save all or none
            save_transactions(created_transactions)

            # Remember which transactions we just created so we can review them
            last_ids = [tx.id for tx in created_transactions]
            session["last_upload_ids"] = last_ids

        except ValueError as e:
            # "Expected" user errors (bad file, bad bank, bad row, etc.)
            return render_template("upload.html", message=str(e))
        except Exception as e:
            # Unexpected errors
            return render_template("upload.html", message=f"Error processing CSV: {e}")

        message = f"Successfully imported {len(created_transactions)} transactions."
        flash(message)
        return redirect(url_for("review_last_upload"))

    @app.route("/review-last-upload", methods=["GET"])
    @login_required
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
            Transaction.query.for_current_user()
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
    @login_required
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
        transactions = Transaction.query.for_current_user().filter(
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
    @login_required
    def list_transactions():
        """
        HTML view: shows all transactions in a table (newest first).
        """
        all_tx = Transaction.query.for_current_user().order_by(Transaction.date.desc()).all()
        return render_template('transactions.html', transactions=all_tx)

    @app.route('/uncategorised')
    @login_required
    def uncategorised_transactions():
        """
        Returns all transactions that are not yet categorised.
        This is what we will send to Claude
        """

        uncats = Transaction.query.for_current_user().filter(
            Transaction.category_id.is_(None)
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
    @login_required
    def uncategorised_view():
        """
        HTML page showing uncategorised transactions in a table.
        """
        uncats = Transaction.query.for_current_user().filter(Transaction.category_id.is_(None)).order_by(
            Transaction.date.desc()
        ).all()

        return render_template('uncategorised.html', transactions=uncats)

    @app.route("/categorise-batch")
    @login_required
    def categorise_batch():
        print("DEBUG: /categorise-batch called") #DEBUG

        uncats = Transaction.query.for_current_user().filter(
            Transaction.category_id.is_(None)
        ).order_by(Transaction.date.desc()).all()

        print(f"DEBUG: found {len(uncats)} uncategorised transactions") #DEBUG

        if not uncats:
            flash("No uncategorised transactions to categorise.")
            return redirect(url_for("home"))

        txs = build_claude_payload(uncats)
        category_names = get_all_category_names()
        categories = categorise_with_claude(txs, category_names)
        print("DEBUG: categories from Claude:", categories) #DEBUG

        updated = 0
        for tx in uncats:
            if tx.id in categories:
                tx.category = categories[tx.id]
                updated += 1

        db.session.commit()
        print(f"DEBUG: updated {updated} rows in DB") #DEBUG
        flash(f"Successfully categorised {updated} transactions.")
        return redirect(url_for("home"))


    @app.route("/plaid/link-token", methods=["POST"])
    @login_required
    def plaid_link_token():
        """Return a short-lived link_token for the frontend to open Plaid Link."""
        token = create_link_token(current_user.id)
        return jsonify({"link_token": token})


    @app.route("/plaid/exchange", methods=["POST"])
    @login_required
    def plaid_exchange():
        """Receive public_token from Plaid Link, exchange for access_token, save PlaidItem + accounts."""
        data = request.get_json()
        result = exchange_public_token(data["public_token"])

        item = PlaidItem(
            user_id=current_user.id,
            access_token=result["access_token"],
            item_id=result["item_id"],
            institution_name=data.get("institution_name", "Unknown"),
        )
        db.session.add(item)
        db.session.flush()

        for acct in data.get("accounts", []):
            account = PlaidAccount(
                user_id=current_user.id,
                item_id=item.id,
                plaid_account_id=acct["id"],
                name=acct["name"],
                mask=acct.get("mask"),
                account_type=acct.get("type"),
            )
            db.session.add(account)

        db.session.commit()
        return jsonify({"status": "ok"})


    @app.route("/plaid/sync", methods=["POST"])
    @login_required
    def plaid_sync():
        """Sync transactions for all linked banks for the current user.
        If item_id is passed in the form, only syncs that specific bank.
        Otherwise, syncs all linked banks.
        """
        item_id = request.form.get("item_id", type=int)
        query = PlaidItem.query.filter_by(user_id=current_user.id)
        items = [query.get(item_id)] if item_id else query.all()
        items = [i for i in items if i]

        total_added = 0
        total_removed = 0

        try:
            for item in items:
                account_map = {a.plaid_account_id: a.name for a in item.accounts}
                added, removed, next_cursor = sync_transactions(item)
                transactions = build_transactions_from_plaid(added, account_map, current_user.id)
                save_transactions(transactions)
                total_added += len(transactions)

                removed_ids = [r["transaction_id"] for r in removed]
                if removed_ids:
                    deleted = Transaction.query.filter(
                        Transaction.plaid_transaction_id.in_(removed_ids),
                        Transaction.user_id == current_user.id
                    ).delete(synchronize_session=False)
                    total_removed += deleted

                item.cursor = next_cursor
                item.last_synced_at = datetime.utcnow()

            db.session.commit()
            flash(f"Synced: {total_added} added, {total_removed} removed.", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Sync failed: {e}", "danger")

        return redirect(url_for("plaid_accounts"))


    @app.route("/plaid/accounts")
    @login_required
    def plaid_accounts():
        """Show all linked bank accounts."""
        items = PlaidItem.query.filter_by(user_id=current_user.id).all()
        return render_template("plaid_accounts.html", items=items)


    @app.route("/plaid/connect")
    @login_required
    def plaid_connect():
        return render_template("plaid_connect.html")

    return app


# ========================================
# START THE APP
# ========================================
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
