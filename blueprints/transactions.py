from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_required, current_user

from models import db, Transaction, Account
from helpers import (
    get_all_category_names,
    build_claude_payload,
    load_uploaded_csv,
    build_transactions_from_df,
    save_transactions,
)
from parsers import parse_standard_csv

from claude_client import categorise_with_claude

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route("/upload-csv", methods=["GET", "POST"])
@login_required
def upload_csv():
    """
    - GET  -> show the HTML form so the user can choose a CSV file
    - POST -> receive the uploaded file, parse it, and store transactions
              in an all-or-nothing way (one bad row = nothing saved).
    """
    if request.method == "GET":
        accounts = Account.query.filter_by(user_id=current_user.id, account_type='manual', status='active').all()
        return render_template("upload.html", accounts=accounts)


    try:
        df = load_uploaded_csv(request)
        account_id = request.form.get("account_id", type=int)
        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
        standard_df = parse_standard_csv(df, account.invert_amounts)
        created_transactions = build_transactions_from_df(standard_df, current_user.id, account.id, account.name)


        save_transactions(created_transactions)

        last_ids = [tx.id for tx in created_transactions]
        session["last_upload_ids"] = last_ids

    except ValueError as e:
        accounts = Account.query.filter_by(user_id=current_user.id, account_type='manual', status='active').all()
        return render_template("upload.html", accounts=accounts, message=str(e))
    except Exception as e:
        accounts = Account.query.filter_by(user_id=current_user.id, account_type='manual', status='active').all()
        return render_template("upload.html", accounts=accounts, message=f"Error processing CSV: {e}")

    message = f"Successfully imported {len(created_transactions)} transactions."
    flash(message)
    return redirect(url_for("transactions.review_last_upload"))


@transactions_bp.route("/review-last-upload", methods=["GET"])
@login_required
def review_last_upload():
    """Show the transactions from the most recent upload."""
    last_ids = session.get("last_upload_ids")

    if not last_ids:
        flash("No recent upload to review.")
        return redirect(url_for("main.home"))

    transactions = (
        Transaction.query.for_current_user()
        .filter(Transaction.id.in_(last_ids))
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .all()
    )

    if not transactions:
        flash("No transactions found for the last upload.")
        return redirect(url_for("main.home"))

    category_names = get_all_category_names()

    return render_template(
        "review_last_upload.html",
        transactions=transactions,
        category_names=category_names
    )


@transactions_bp.route("/update-categories", methods=["POST"])
@login_required
def update_categories():
    """
    Update categories for the transactions in the last upload.
    Optionally send remaining uncategorised ones to Claude.
    """
    last_ids = session.get("last_upload_ids")
    if not last_ids:
        flash("No recent upload to update.")
        return redirect(url_for("transactions.upload_csv"))

    transactions = Transaction.query.for_current_user().filter(
        Transaction.id.in_(last_ids)
    ).all()

    for tx in transactions:
        field_name = f"category_{tx.id}"
        new_cat = request.form.get(field_name) or None
        tx.category = new_cat

    db.session.commit()

    action = request.form.get("action")

    print("DEBUG action =", action)  # DEBUG

    if action == "send_to_claude":
        uncats = [t for t in transactions if t.category is None]
        if not uncats:
            flash("No uncategorised transactions to send to Claude.")
            return redirect(url_for("transactions.review_last_upload"))

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
        for tx in transactions:
            tx.category = None
        db.session.commit()
        flash("All categories reset to Uncategorised.")
        return redirect(url_for("transactions.review_last_upload"))

    else:
        flash("Categories updated.")

    return redirect(url_for("transactions.review_last_upload"))


@transactions_bp.route('/transactions')
@login_required
def list_transactions():
    """HTML view: shows all transactions in a table (newest first)."""
    all_tx = Transaction.query.for_current_user().order_by(Transaction.date.desc()).all()
    return render_template('transactions.html', transactions=all_tx)


@transactions_bp.route('/uncategorised')
@login_required
def uncategorised_transactions():
    """Returns all transactions that are not yet categorised (JSON)."""
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


@transactions_bp.route('/uncategorised-view')
@login_required
def uncategorised_view():
    """HTML page showing uncategorised transactions in a table."""
    uncats = Transaction.query.for_current_user().filter(
        Transaction.category_id.is_(None)
    ).order_by(Transaction.date.desc()).all()

    return render_template('uncategorised.html', transactions=uncats)


@transactions_bp.route("/categorise-batch")
@login_required
def categorise_batch():
    print("DEBUG: /categorise-batch called")  # DEBUG

    uncats = Transaction.query.for_current_user().filter(
        Transaction.category_id.is_(None)
    ).order_by(Transaction.date.desc()).all()

    print(f"DEBUG: found {len(uncats)} uncategorised transactions")  # DEBUG

    if not uncats:
        flash("No uncategorised transactions to categorise.")
        return redirect(url_for("main.home"))

    txs = build_claude_payload(uncats)
    category_names = get_all_category_names()
    categories = categorise_with_claude(txs, category_names)
    print("DEBUG: categories from Claude:", categories)  # DEBUG

    updated = 0
    for tx in uncats:
        if tx.id in categories:
            tx.category = categories[tx.id]
            updated += 1

    db.session.commit()
    print(f"DEBUG: updated {updated} rows in DB")  # DEBUG
    flash(f"Successfully categorised {updated} transactions.")
    return redirect(url_for("main.home"))
