from flask import render_template, redirect, url_for, flash, request, make_response
import csv
import io

from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.expenses import bp
from app.expenses.forms import ExpenseForm
from app.models import Expense, Category

@bp.route('/')
@login_required
def index():
    # Alle Ausgaben des Users holen, sortiert nach Datum (neueste zuerst)
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    return render_template('expenses/index.html', expenses=expenses)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = ExpenseForm()
    # Dropdown mit Kategorien des Users füllen: (ID, Name)
    form.category.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id).all()]
    
    if request.method == 'GET':
        form.date.data = datetime.today() # Heutiges Datum vorausfüllen

    if form.validate_on_submit():
        expense = Expense(
            amount=form.amount.data,
            category_id=form.category.data,
            date=form.date.data,
            note=form.note.data,
            user_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Ausgabe hinzugefügt!', 'success')
        return redirect(url_for('expenses.index'))
        
    return render_template('expenses/form.html', form=form, title="Neue Ausgabe")

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = ExpenseForm(obj=expense)
    
    # Auch beim Bearbeiten müssen die Kategorien geladen werden
    form.category.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id).all()]
    
    # Beim ersten Laden (GET) die ID der aktuellen Kategorie setzen
    if request.method == 'GET':
        form.category.data = expense.category_id

    if form.validate_on_submit():
        expense.amount = form.amount.data
        expense.category_id = form.category.data
        expense.date = form.date.data
        expense.note = form.note.data
        db.session.commit()
        flash('Ausgabe aktualisiert.', 'success')
        return redirect(url_for('expenses.index'))
        
    return render_template('expenses/form.html', form=form, title="Ausgabe bearbeiten")

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    flash('Ausgabe gelöscht.', 'success')
    return redirect(url_for('expenses.index'))

@bp.route('/export')
@login_required
def export():
    # 1. Daten holen
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()

    # 2. CSV im Arbeitsspeicher erstellen (StringIO ist wie eine Datei im RAM)
    si = io.StringIO()
    cw = csv.writer(si, delimiter=';') # Excel in Deutschland mag oft Strichpunkte
    
    # Header schreiben
    cw.writerow(['Datum', 'Kategorie', 'Betrag', 'Währung', 'Notiz'])

    # Zeilen schreiben
    for expense in expenses:
        category_name = expense.category.name if expense.category else 'Keine'
        # Wir formatieren das Datum und den Betrag für Excel-Freundlichkeit
        cw.writerow([
            expense.date.strftime('%d.%m.%Y'),
            category_name,
            str(expense.amount).replace('.', ','), # Deutsche Kommas für Zahlen
            expense.currency,
            expense.note
        ])

    # 3. Antwort als Datei-Download zurückgeben
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=meine_ausgaben.csv"
    output.headers["Content-type"] = "text/csv"
    return output