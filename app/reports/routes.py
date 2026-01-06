from flask import render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, date
from app import db
from app.reports import bp
from app.models import Expense, Category

@bp.route('/monthly')
@login_required
def monthly():
    # 1. Welcher Monat soll angezeigt werden? (Standard: aktueller Monat)
    selected_month_str = request.args.get('month')
    
    if selected_month_str:
        year, month = map(int, selected_month_str.split('-'))
    else:
        today = date.today()
        year, month = today.year, today.month
        selected_month_str = today.strftime('%Y-%m')

    # 2. Gesamtsumme für diesen Monat berechnen
    # SQL: SELECT SUM(amount) FROM expense WHERE user_id=... AND year=... AND month=...
    total_spend = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        func.extract('year', Expense.date) == year,
        func.extract('month', Expense.date) == month
    ).scalar() or 0  # "or 0", falls keine Ausgaben da sind (None)

    # 3. Ausgaben nach Kategorie gruppieren
    # SQL: SELECT category.name, SUM(expense.amount) ... GROUP BY category.name
    category_breakdown = db.session.query(
        Category.name, 
        func.sum(Expense.amount)
    ).join(Expense).filter(
        Expense.user_id == current_user.id,
        func.extract('year', Expense.date) == year,
        func.extract('month', Expense.date) == month
    ).group_by(Category.name).all()

    return render_template(
        'reports/monthly.html', 
        total_spend=total_spend,
        category_breakdown=category_breakdown,
        selected_month=selected_month_str
    )