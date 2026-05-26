"""
conftest.py – Shared pytest fixtures for the Expense Tracker test suite.

All tests run against an in-memory SQLite database so they are
self-contained, fast, and never touch a real database.
"""

import pytest
from app import create_app, db as _db
from app.models import User, Expense, Category


# ---------------------------------------------------------------------------
# App & DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Create a Flask application configured for testing (session-scoped)."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False,          # Disable CSRF for API tests
        "SECRET_KEY": "test-secret-key",
        "LOGIN_DISABLED": False,
    }
    application = create_app(test_config)
    return application


@pytest.fixture(scope="function")
def db(app):
    """
    Provide a fresh database for every single test function.
    Tables are created before each test and dropped afterwards.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Flask test client – each test gets a clean HTTP client + empty DB."""
    return app.test_client()


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_user(db, app):
    """Create and persist a standard test user."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return {"id": user.id, "email": user.email, "password": "SecurePass123!"}


@pytest.fixture()
def second_user(db, app):
    """Create a second user for isolation / cross-user access tests."""
    with app.app_context():
        user = User(username="otheruser", email="other@example.com")
        user.set_password("OtherPass456!")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return {"id": user.id, "email": user.email, "password": "OtherPass456!"}


@pytest.fixture()
def auth_client(client, test_user):
    """Return a test client that is already logged in as test_user."""
    client.post(
        "/auth/login",
        data={"email": test_user["email"], "password": test_user["password"]},
        follow_redirects=True,
    )
    return client


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_category(db, app, test_user):
    """Create a default expense category owned by test_user."""
    with app.app_context():
        cat = Category(name="Food", user_id=test_user["id"])
        db.session.add(cat)
        db.session.commit()
        db.session.refresh(cat)
        return {"id": cat.id, "name": cat.name}


@pytest.fixture()
def test_expense(db, app, test_user, test_category):
    """Create a default expense for test_user."""
    with app.app_context():
        expense = Expense(
            title="Lunch",
            amount=12.50,
            category_id=test_category["id"],
            user_id=test_user["id"],
            description="Team lunch",
        )
        db.session.add(expense)
        db.session.commit()
        db.session.refresh(expense)
        return {"id": expense.id, "title": expense.title, "amount": expense.amount}
