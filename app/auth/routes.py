from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from urllib.parse import urlsplit
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # Prüfen ob User existiert und Passwort stimmt
        if user is None or not user.check_password(form.password.data):
            flash('Ungültige Email oder Passwort', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        
        # Sicherstellen, dass "next" redirect sicher ist
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
            
        return redirect(next_page)
        
    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registrierung erfolgreich! Bitte logge dich ein.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', title='Registrieren', form=form)