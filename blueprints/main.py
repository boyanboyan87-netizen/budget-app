from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user

from models import db, Transaction

main_bp = Blueprint('main', __name__)


def get_all_routes() -> list[dict]:
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        routes.append({
            'endpoint': rule.endpoint,
            'rule': str(rule),
            'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        })
    routes.sort(key=lambda r: r['rule'])
    return routes


@main_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return render_template("landing.html")


@main_bp.route("/dashboard")
@login_required
def home():
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


@main_bp.route('/db-info')
def db_info():
    """Show which database we're connected to"""
    return {
        'database_url': 'PostgreSQL on Neon',
        'dialect': db.engine.dialect.name,
        'driver': db.engine.driver,
    }
