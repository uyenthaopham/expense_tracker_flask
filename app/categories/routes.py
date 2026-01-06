from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.categories import bp
from app.categories.forms import CategoryForm
from app.models import Category

@bp.route('/')
@login_required
def index():
    # Nur Kategorien des aktuellen Users anzeigen
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories/index.html', categories=categories)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = CategoryForm()
    if form.validate_on_submit():
        # Prüfen, ob Kategorie schon existiert (für diesen User)
        exists = Category.query.filter_by(user_id=current_user.id, name=form.name.data).first()
        if exists:
            flash('Diese Kategorie existiert bereits.', 'warning')
        else:
            category = Category(name=form.name.data, user_id=current_user.id)
            db.session.add(category)
            db.session.commit()
            flash('Kategorie erstellt!', 'success')
            return redirect(url_for('categories.index'))
    return render_template('categories/form.html', form=form, title="Neue Kategorie")

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    # Sicherstellen, dass die Kategorie dem User gehört
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        category.name = form.name.data
        try:
            db.session.commit()
            flash('Kategorie aktualisiert.', 'success')
            return redirect(url_for('categories.index'))
        except:
            db.session.rollback()
            flash('Fehler beim Speichern (Name evtl. doppelt?)', 'danger')
            
    return render_template('categories/form.html', form=form, title="Kategorie bearbeiten")

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(category)
    db.session.commit()
    flash('Kategorie gelöscht.', 'success')
    return redirect(url_for('categories.index'))