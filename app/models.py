from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        # Wir speichern niemals das Passwort im Klartext!
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'
    


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Beziehung: Ein User hat viele Kategorien
    user = db.relationship('User', backref=db.backref('categories', lazy=True))

    # Constraint: Name muss pro User einzigartig sein (kein doppeltes "Essen")
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='unique_user_category_name'),
    )

    def __repr__(self):
        return f'<Category {self.name}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR')
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    note = db.Column(db.String(200))

    # Verknüpfungen (Foreign Keys)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True) # Nullable, falls Kategorie gelöscht wird

    # Beziehungen für einfachen Zugriff (expense.category.name)
    category = db.relationship('Category', backref='expenses')
    user = db.relationship('User', backref='expenses')

    def __repr__(self):
        return f'<Expense {self.amount} - {self.note}>'

# Diese Funktion braucht Flask-Login, um den User aus der DB zu laden
@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))