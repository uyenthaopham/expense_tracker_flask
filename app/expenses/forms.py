from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ExpenseForm(FlaskForm):
    amount = FloatField('Betrag', validators=[DataRequired(), NumberRange(min=0.01)])
    category = SelectField('Kategorie', coerce=int, validators=[DataRequired()])
    date = DateField('Datum', format='%Y-%m-%d', validators=[DataRequired()])
    note = StringField('Notiz (optional)')
    submit = SubmitField('Speichern')