from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Account, PlaidItem

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route("/accounts")
@login_required
def accounts():
    # Automatic accounts: grouped by bank (PlaidItem), includes balance + sync
    items = PlaidItem.query.filter_by(user_id=current_user.id).all()

    # Manual accounts: user-created, no Plaid connection
    manual_accounts = Account.query.filter_by(
        user_id=current_user.id,
        account_type='manual',
        status='active'
    ).all()

    return render_template("accounts.html", items=items, manual_accounts=manual_accounts)


@accounts_bp.route("/accounts/new", methods=["GET", "POST"])
@login_required
def new_account():
    if request.method == "GET":
        return render_template("account_form.html")

    # Parse invert_amounts: "true" → True, "false" → False, "" → None
    raw = request.form.get("invert_amounts")
    invert = True if raw == "true" else (False if raw == "false" else None)

    account = Account(
        user_id=current_user.id,
        name=request.form.get("name"),
        currency=request.form.get("currency", "GBP"),
        invert_amounts=invert,
        account_type='manual',
        status='active',
    )
    db.session.add(account)
    db.session.commit()

    flash(f"Account '{account.name}' created.", "success")
    return redirect(url_for("accounts.accounts"))


@accounts_bp.route("/accounts/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_account(id):
    # Fetch account — verify it belongs to current user and is manual
    account = Account.query.filter_by(
        id=id,
        user_id=current_user.id,
        account_type='manual'
    ).first_or_404()

    if request.method == "GET":
        return render_template("account_form.html", account=account)

    # Parse invert_amounts: "true" → True, "false" → False, "" → None
    raw = request.form.get("invert_amounts")
    invert = True if raw == "true" else (False if raw == "false" else None)

    account.name = request.form.get("name")
    account.currency = request.form.get("currency", "GBP")
    account.invert_amounts = invert

    db.session.commit()

    flash(f"Account '{account.name}' updated.", "success")
    return redirect(url_for("accounts.accounts"))

