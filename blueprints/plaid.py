from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from models import db, Transaction, PlaidItem, Account, AccountBalance
from plaid_client import create_link_token, exchange_public_token, sync_transactions, get_balances

from helpers import build_transactions_from_plaid, save_transactions

plaid_bp = Blueprint('plaid', __name__)


@plaid_bp.route("/plaid/link-token", methods=["POST"])
@login_required
def plaid_link_token():
    """Return a short-lived link_token for the frontend to open Plaid Link."""
    token = create_link_token(current_user.id)
    return jsonify({"link_token": token})


@plaid_bp.route("/plaid/exchange", methods=["POST"])
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
        account = Account(
            user_id=current_user.id,
            item_id=item.id,
            plaid_account_id=acct["id"],
            name=acct["name"],
            mask=acct.get("mask"),
            account_type='automatic',        # hardcoded — all Plaid accounts are automatic
            subtype=acct.get("type"),       # Plaid's type e.g. 'depository', 'credit'
        )
        db.session.add(account)

    db.session.commit()
    return jsonify({"status": "ok"})


@plaid_bp.route("/plaid/sync", methods=["POST"])
@login_required
def plaid_sync():
    """Sync transactions for all linked banks for the current user.
    If item_id is passed in the form, only syncs that specific bank.
    """
    item_id = request.form.get("item_id", type=int)
    if item_id:
        item = PlaidItem.query.filter_by(user_id=current_user.id, id=item_id).first()
        items = [item] if item else []
    else:
        items = PlaidItem.query.filter_by(user_id=current_user.id).all()

    total_added = 0
    total_removed = 0

    try:
        for item in items:
            account_map = {a.plaid_account_id: a.id for a in item.accounts}     # now maps to id
            added, removed, next_cursor = sync_transactions(item)
            transactions = build_transactions_from_plaid(added, account_map, current_user.id)
            save_transactions(transactions)
            balances = get_balances(item)

            for b in balances:
                db_id = account_map.get(b['plaid_account_id'])           
                
                if db_id:
                    snapshot = AccountBalance(
                        account_id=db_id,
                        current_balance=b['current'],
                        currency=b['currency'],
                        recorded_at=datetime.utcnow(),
                    )
                    db.session.add(snapshot)
            
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

    return redirect(url_for("plaid.plaid_accounts"))


@plaid_bp.route("/plaid/accounts")
@login_required
def plaid_accounts():
    """Show all linked bank accounts."""
    items = PlaidItem.query.filter_by(user_id=current_user.id).all()
    return render_template("plaid_accounts.html", items=items)


@plaid_bp.route("/plaid/connect")
@login_required
def plaid_connect():
    return render_template("plaid_connect.html")
