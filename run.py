from app import create_app, db
from flask_migrate import upgrade
from app.models import User, Expense

app = create_app()


with app.app_context():
    try:
        upgrade()
        print("Datenbank-Upgrade erfolgreich durchgeführt!")
    except Exception as e:
        print(f"Fehler beim Datenbank-Upgrade: {e}")
        # Falls upgrade fehlschlägt (z.B. weil migrations fehlen),
        # versuchen wir create_all als Notlösung (nur für erste Erstellung)
        try:
            db.create_all()
            print("Tabellen via create_all erstellt.")
        except Exception as e2:
            print(f"Kritischer Datenbank-Fehler: {e2}")

if __name__ == '__main__':
    app.run(debug=True)