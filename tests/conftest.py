"""Shared test fixtures for the budget app test suite."""
import pytest
from datetime import date

from app import create_app
from models import db, User, Transaction


TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "SECRET_KEY": "test-secret",
    "WTF_CSRF_ENABLED": False,
}


@pytest.fixture
def app():
    """Create a test app with an in-memory SQLite database."""
    app = create_app(TEST_CONFIG)
    yield app


@pytest.fixture
def client(app):
    """A test HTTP client for route testing."""
    return app.test_client()


@pytest.fixture
def two_users(app):
    """Create two isolated users and a transaction each. Returns (user1, user2)."""
    with app.app_context():
        alice = User(email="alice@test.com", first_name="Alice")
        bob = User(email="bob@test.com", first_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        tx_alice = Transaction(
            user_id=alice.id,
            date=date(2024, 1, 1),
            amount=10.00,
            description="Alice coffee",
            account="Main",
        )
        tx_bob = Transaction(
            user_id=bob.id,
            date=date(2024, 1, 2),
            amount=20.00,
            description="Bob coffee",
            account="Main",
        )
        db.session.add_all([tx_alice, tx_bob])
        db.session.commit()

        yield alice.id, bob.id
