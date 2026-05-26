# scripts/seed_benchmark.py
import time
from app import create_app, db
from app.models import Expense, User, Category
import random
from datetime import date, timedelta

def seed(n=200_000):
    users = User.query.all()
    categories = Category.query.all()

    if not users:
        raise RuntimeError("No users found. Create at least one user first.")

    category_ids = [c.id for c in categories] or [None]

    # Xóa seed cũ
    deleted = Expense.query.filter(
        Expense.note.like("bench seed %")
    ).delete(synchronize_session=False)
    db.session.commit()
    if deleted:
        print(f"Cleaned up {deleted} old seed rows")

    # Build list of dicts thay vì list of ORM objects → nhanh hơn 3-5x
    rows = [
        {
            "user_id": random.choice(users).id,
            "amount": round(random.uniform(1, 500), 2),
            "date": date.today() - timedelta(days=random.randint(0, 730)),
            "category_id": random.choice(category_ids),
            "note": f"bench seed {i}",
        }
        for i in range(n)
    ]

    t0 = time.perf_counter()
    db.session.execute(db.insert(Expense), rows)
    db.session.commit()
    elapsed = time.perf_counter() - t0

    print(f"Done: {n:,} expenses seeded in {elapsed:.2f}s")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed(200_000)