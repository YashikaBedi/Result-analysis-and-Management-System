from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, NumberRange
from app.models import User


class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80)
    ])
    password = PasswordField('Password', validators=[
                             DataRequired(message='Password is required')])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    """User registration form"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    full_name = StringField('Full Name', validators=[
                            DataRequired(), Length(min=2, max=120)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[
                       ('student', 'Student'), ('faculty', 'Faculty')], validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        """Check if username already exists"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(
                'Username already taken. Please choose a different one.')

    def validate_email(self, email):
        """Check if email already exists"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError(
                'Email already registered. Please use a different one.')


class InternalExamForm(FlaskForm):
    """Form for internal exam marks"""
    student_id = StringField('Student ID', validators=[DataRequired()])
    course_id = IntegerField('Course ID', validators=[DataRequired()])

    cie_assessment_1 = FloatField('CIE Assessment 1 (out of 10)', validators=[
        DataRequired(),
        NumberRange(min=0, max=10)
    ])
    cie_assessment_2 = FloatField('CIE Assessment 2 (out of 10)', validators=[
        DataRequired(),
        NumberRange(min=0, max=10)
    ])
    cie_assessment_3 = FloatField('CIE Assessment 3 (out of 10)', validators=[
        DataRequired(),
        NumberRange(min=0, max=10)
    ])
    mid_term_marks = FloatField('Mid Term Marks (out of 20)', validators=[
        DataRequired(),
        NumberRange(min=0, max=20)
    ])
    assignment_marks = FloatField('Assignment Marks (out of 10)', validators=[
        DataRequired(),
        NumberRange(min=0, max=10)
    ])
    remarks = TextAreaField('Remarks', validators=[Length(max=500)])
    submit = SubmitField('Save Internal Exam')


class ExternalExamForm(FlaskForm):
    """Form for external exam marks"""
    student_id = StringField('Student ID', validators=[DataRequired()])
    course_id = IntegerField('Course ID', validators=[DataRequired()])
    external_marks = FloatField('External Exam Marks (out of 60)', validators=[
        DataRequired(),
        NumberRange(min=0, max=60)
    ])
    remarks = TextAreaField('Remarks', validators=[Length(max=500)])
    submit = SubmitField('Save External Exam')


class PlacementPrepForm(FlaskForm):
    """Form for placement preparation scores"""
    student_id = StringField('Student ID', validators=[DataRequired()])

    dsa_mock_exam = FloatField('DSA Mock Exam Score (out of 100)', validators=[
        NumberRange(min=0, max=100)
    ])
    oops_mock_exam = FloatField('OOPS Mock Exam Score (out of 100)', validators=[
        NumberRange(min=0, max=100)
    ])
    dbms_mock_exam = FloatField('DBMS Mock Exam Score (out of 100)', validators=[
        NumberRange(min=0, max=100)
    ])
    programming_mock_exam = FloatField('Programming Mock Exam Score (out of 100)', validators=[
        NumberRange(min=0, max=100)
    ])
    aptitude_score = FloatField('Aptitude Test Score (out of 100)', validators=[
        NumberRange(min=0, max=100)
    ])
    interview_score = FloatField('Mock Interview Score (out of 100)', validators=[
        NumberRange(min=0, max=100)
    ])

    remarks = TextAreaField('Remarks', validators=[Length(max=500)])
    submit = SubmitField('Save Placement Preparation')


class UpdateProfileForm(FlaskForm):
    """Form to update user profile"""
    full_name = StringField('Full Name', validators=[
                            DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField(
        'Current Password (required to change details)', validators=[DataRequired()])
    submit = SubmitField('Update Profile')

    def validate_email(self, email):
        """Check if new email is not already taken"""
        from flask_login import current_user
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already registered.')


class CreateDepartmentForm(FlaskForm):
    """Form to create department"""
    name = StringField('Department Name', validators=[
                       DataRequired(), Length(min=2, max=100)])
    code = StringField('Department Code', validators=[
                       DataRequired(), Length(min=2, max=10)])
    submit = SubmitField('Create Department')


class CreateCourseForm(FlaskForm):
    """Form to create course"""
    course_code = StringField('Course Code', validators=[
                              DataRequired(), Length(min=2, max=20)])
    course_name = StringField('Course Name', validators=[
                              DataRequired(), Length(min=2, max=150)])
    credits = IntegerField('Credits', validators=[
                           DataRequired(), NumberRange(min=1, max=8)])
    submit = SubmitField('Create Course')
