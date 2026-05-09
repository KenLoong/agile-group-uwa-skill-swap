from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email    = StringField('UWA Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password')],
    )
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        if not email.data.endswith('@student.uwa.edu.au'):
            raise ValidationError('Please use your UWA student email.')
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered.')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose another.')


class LoginForm(FlaskForm):
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Login')


class PostForm(FlaskForm):
    title       = StringField('Skill Title',   validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category_id = SelectField('Category',      coerce=int, validators=[DataRequired()])
    status      = SelectField(
        'Status',
        choices=[
            ('open',    '🟢 Open – looking for a swap partner'),
            ('matched', '🤝 Matched – already found someone'),
            ('closed',  '⭕ Closed – no longer available'),
        ],
        default='open',
    )
    tags = StringField(
        'Tags',
        validators=[Optional(), Length(max=300)],
        description='Comma-separated keywords, e.g. python, beginner, cits1401',
    )
    image = FileField(
        'Cover image',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'webp', 'gif'], 'Use PNG, JPG, WebP, or GIF.'),
        ],
    )
    remove_image = BooleanField('Remove current image')
    submit       = SubmitField('Post Skill')


class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit  = SubmitField('Post Comment')
