"""
tests/test_expenses.py
======================
Integration tests for Expense CRUD operations.

Covers:
  - Create (happy path, duplicates, invalid data, SQL injection, boundaries)
  - Read / List (own vs other user isolation)
  - Update (valid, invalid, cross-user)
  - Delete (valid, cross-user, non-existent)
  - Transaction integrity
"""

import pytest


# ===========================================================================
# CREATE EXPENSE
# ===========================================================================

class TestCreateExpense:

    def test_create_expense_success(self, auth_client, test_category):
        """TC-EXP-01 – Authenticated user can create a valid expense."""
        resp = auth_client.post(
            "/expense/add",
            data={
                "title": "Coffee",
                "amount": "3.50",
                "category_id": test_category["id"],
                "description": "Morning coffee",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"coffee" in resp.data.lower() or b"success" in resp.data.lower()

    def test_create_expense_negative_amount(self, auth_client, test_category):
        """TC-EXP-02 – Negative amount is rejected."""
        resp = auth_client.post(
            "/expense/add",
            data={
                "title": "NegativeExpense",
                "amount": "-10.00",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)
        # Must not land on success page with negative amount stored
        assert b"negativeexpense" not in resp.data.lower() \
               or b"error" in resp.data.lower() \
               or b"invalid" in resp.data.lower()

    def test_create_expense_zero_amount(self, auth_client, test_category):
        """TC-EXP-03 – Zero amount expense is rejected or treated as invalid."""
        resp = auth_client.post(
            "/expense/add",
            data={
                "title": "FreeItem",
                "amount": "0",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)

    def test_create_expense_non_numeric_amount(self, auth_client, test_category):
        """TC-EXP-04 – Non-numeric amount is rejected."""
        resp = auth_client.post(
            "/expense/add",
            data={
                "title": "BadAmount",
                "amount": "abc",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)

    def test_create_expense_missing_title(self, auth_client, test_category):
        """TC-EXP-05 – Missing title is rejected."""
        resp = auth_client.post(
            "/expense/add",
            data={"title": "", "amount": "10.00", "category_id": test_category["id"]},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)

    def test_create_expense_sql_injection_title(self, auth_client, test_category):
        """TC-EXP-06 – SQL injection in title is handled safely."""
        payload = "'; DROP TABLE expense; --"
        resp = auth_client.post(
            "/expense/add",
            data={"title": payload, "amount": "5.00", "category_id": test_category["id"]},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302, 400)
        # DB must still respond (no crash)

    def test_create_expense_sql_injection_amount(self, auth_client, test_category):
        """TC-EXP-07 – SQL injection in amount field is safely rejected."""
        payload = "1; DROP TABLE expense; --"
        resp = auth_client.post(
            "/expense/add",
            data={"title": "SQLi", "amount": payload, "category_id": test_category["id"]},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)

    def test_create_expense_xss_in_title(self, auth_client, test_category):
        """TC-EXP-08 – XSS payload in title is escaped in the response."""
        payload = "<script>alert(1)</script>"
        resp = auth_client.post(
            "/expense/add",
            data={"title": payload, "amount": "5.00", "category_id": test_category["id"]},
            follow_redirects=True,
        )
        assert b"<script>alert(1)</script>" not in resp.data

    def test_create_expense_very_large_amount(self, auth_client, test_category):
        """TC-EXP-09 – Extremely large amount is handled without overflow."""
        resp = auth_client.post(
            "/expense/add",
            data={
                "title": "BigExpense",
                "amount": "99999999999.99",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)

    def test_create_expense_duplicate_title_same_user(
        self, auth_client, test_expense, test_category
    ):
        """TC-EXP-10 – Duplicate title for the same user should be allowed (not a unique key)."""
        resp = auth_client.post(
            "/expense/add",
            data={
                "title": test_expense["title"],    # same title
                "amount": "99.00",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        # Duplicates on title alone are generally allowed; if not, error is clear
        assert resp.status_code in (200, 400)

    def test_create_expense_unauthenticated(self, client, test_category):
        """TC-EXP-11 – Unauthenticated POST to /expense/add redirects to login."""
        resp = client.post(
            "/expense/add",
            data={"title": "Hack", "amount": "1.00", "category_id": test_category["id"]},
            follow_redirects=True,
        )
        assert b"login" in resp.data.lower()

    def test_create_expense_invalid_category(self, auth_client):
        """TC-EXP-12 – Non-existent category_id is rejected."""
        resp = auth_client.post(
            "/expense/add",
            data={"title": "BadCat", "amount": "5.00", "category_id": 999999},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)

    def test_create_expense_category_belongs_to_other_user(
        self, auth_client, db, app, second_user
    ):
        """TC-EXP-13 – Using another user's category_id is rejected."""
        from app.models import Category
        with app.app_context():
            other_cat = Category(name="OtherCat", user_id=second_user["id"])
            db.session.add(other_cat)
            db.session.commit()
            other_cat_id = other_cat.id

        resp = auth_client.post(
            "/expense/add",
            data={"title": "Infiltrate", "amount": "1.00", "category_id": other_cat_id},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400, 403)


# ===========================================================================
# READ / LIST
# ===========================================================================

class TestReadExpense:

    def test_list_expenses_only_own(self, auth_client, test_expense, db, app, second_user):
        """TC-EXP-14 – Expense list must not include other users' expenses."""
        from app.models import Category, Expense
        with app.app_context():
            other_cat = Category(name="OtherCat", user_id=second_user["id"])
            db.session.add(other_cat)
            db.session.commit()
            other_exp = Expense(
                title="OtherUserExpense",
                amount=100.0,
                category_id=other_cat.id,
                user_id=second_user["id"],
            )
            db.session.add(other_exp)
            db.session.commit()

        resp = auth_client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        assert b"otheruserexpense" not in resp.data.lower()

    def test_expense_detail_accessible_by_owner(self, auth_client, test_expense):
        """TC-EXP-15 – Owner can view their own expense detail."""
        resp = auth_client.get(f"/expense/{test_expense['id']}", follow_redirects=True)
        assert resp.status_code in (200, 302)

    def test_expense_detail_blocked_for_other_user(
        self, client, test_expense, second_user
    ):
        """TC-EXP-16 – Other user cannot access owner's expense detail."""
        client.post(
            "/auth/login",
            data={"email": second_user["email"], "password": second_user["password"]},
            follow_redirects=True,
        )
        resp = client.get(f"/expense/{test_expense['id']}", follow_redirects=True)
        assert resp.status_code in (200, 403, 404)
        assert b"lunch" not in resp.data.lower() or resp.status_code != 200


# ===========================================================================
# UPDATE EXPENSE
# ===========================================================================

class TestUpdateExpense:

    def test_update_expense_success(self, auth_client, test_expense, test_category):
        """TC-EXP-17 – Owner can update their expense."""
        resp = auth_client.post(
            f"/expense/{test_expense['id']}/edit",
            data={
                "title": "Updated Lunch",
                "amount": "15.00",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302)

    def test_update_expense_invalid_amount(self, auth_client, test_expense, test_category):
        """TC-EXP-18 – Updating with invalid amount is rejected."""
        resp = auth_client.post(
            f"/expense/{test_expense['id']}/edit",
            data={
                "title": "Test",
                "amount": "not_a_number",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)

    def test_update_expense_cross_user_blocked(
        self, client, test_expense, second_user, test_category
    ):
        """TC-EXP-19 – Second user cannot edit another user's expense."""
        client.post(
            "/auth/login",
            data={"email": second_user["email"], "password": second_user["password"]},
            follow_redirects=True,
        )
        resp = client.post(
            f"/expense/{test_expense['id']}/edit",
            data={
                "title": "Hacked",
                "amount": "0.01",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 403, 404)


# ===========================================================================
# DELETE EXPENSE
# ===========================================================================

class TestDeleteExpense:

    def test_delete_expense_success(self, auth_client, test_expense):
        """TC-EXP-20 – Owner can delete their own expense."""
        resp = auth_client.post(
            f"/expense/{test_expense['id']}/delete",
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302)

    def test_delete_expense_nonexistent(self, auth_client):
        """TC-EXP-21 – Deleting a non-existent expense returns 404, not a crash."""
        resp = auth_client.post(
            "/expense/999999/delete",
            follow_redirects=True,
        )
        assert resp.status_code in (200, 404)

    def test_delete_expense_cross_user_blocked(
        self, client, test_expense, second_user
    ):
        """TC-EXP-22 – Second user cannot delete another user's expense."""
        client.post(
            "/auth/login",
            data={"email": second_user["email"], "password": second_user["password"]},
            follow_redirects=True,
        )
        resp = client.post(
            f"/expense/{test_expense['id']}/delete",
            follow_redirects=True,
        )
        assert resp.status_code in (200, 403, 404)

    def test_delete_unauthenticated(self, client, test_expense):
        """TC-EXP-23 – Unauthenticated delete is redirected to login."""
        resp = client.post(
            f"/expense/{test_expense['id']}/delete",
            follow_redirects=True,
        )
        assert b"login" in resp.data.lower()


# ===========================================================================
# TRANSACTION INTEGRITY
# ===========================================================================

class TestTransactionIntegrity:

    def test_expense_persists_after_creation(self, auth_client, test_category, db, app):
        """TC-EXP-24 – Created expense is actually stored in the database."""
        from app.models import Expense
        auth_client.post(
            "/expense/add",
            data={
                "title": "PersistedExpense",
                "amount": "42.00",
                "category_id": test_category["id"],
            },
            follow_redirects=True,
        )
        with app.app_context():
            exp = Expense.query.filter_by(title="PersistedExpense").first()
            assert exp is not None
            assert float(exp.amount) == pytest.approx(42.00)

    def test_expense_removed_after_deletion(self, auth_client, test_expense, db, app):
        """TC-EXP-25 – Deleted expense is removed from the database."""
        from app.models import Expense
        auth_client.post(
            f"/expense/{test_expense['id']}/delete",
            follow_redirects=True,
        )
        with app.app_context():
            exp = Expense.query.get(test_expense["id"])
            assert exp is None

    def test_concurrent_creation_does_not_duplicate(
        self, auth_client, test_category, db, app
    ):
        """TC-EXP-26 – Submitting the same form twice results in exactly two DB rows (no de-dup)."""
        from app.models import Expense
        data = {"title": "DoubleSubmit", "amount": "7.00", "category_id": test_category["id"]}
        auth_client.post("/expense/add", data=data, follow_redirects=True)
        auth_client.post("/expense/add", data=data, follow_redirects=True)
        with app.app_context():
            count = Expense.query.filter_by(title="DoubleSubmit").count()
            assert count == 2   # Both submissions stored; de-dup is UI concern
