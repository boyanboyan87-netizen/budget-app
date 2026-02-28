"""Tests for UserScopedQuery — verifies user data isolation."""
from models import Transaction


class TestUserScopedQuery:
    """for_user() must return only that user's transactions."""

    def test_alice_sees_only_her_transactions(self, app, two_users):
        alice_id, bob_id = two_users
        with app.app_context():
            results = Transaction.query.for_user(alice_id).all()
            assert len(results) == 1
            assert results[0].description == "Alice coffee"

    def test_bob_sees_only_his_transactions(self, app, two_users):
        alice_id, bob_id = two_users
        with app.app_context():
            results = Transaction.query.for_user(bob_id).all()
            assert len(results) == 1
            assert results[0].description == "Bob coffee"

    def test_alice_cannot_see_bobs_transactions(self, app, two_users):
        alice_id, bob_id = two_users
        with app.app_context():
            results = Transaction.query.for_user(alice_id).all()
            descriptions = [t.description for t in results]
            assert "Bob coffee" not in descriptions

    def test_unknown_user_sees_no_transactions(self, app, two_users):
        with app.app_context():
            results = Transaction.query.for_user(99999).all()
            assert results == []

    def test_total_transactions_in_db(self, app, two_users):
        """Sanity check: both users' transactions exist in the DB."""
        with app.app_context():
            total = Transaction.query.count()
            assert total == 2
