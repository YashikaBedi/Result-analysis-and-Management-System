from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db
from enum import Enum

class UserRole(Enum):
    """User roles in the system"""
    ADMIN = 'admin'  # College administrator
    FACULTY = 'faculty'  # Teaching faculty/examiner
    STUDENT = 'student'  # Student
    HOD = 'hod'  # Head of Department


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.STUDENT.value)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    departments = db.relationship('Department', secondary='faculty_department', backref='faculty_members')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


# Association table for faculty and departments
faculty_department = db.Table(
    'faculty_department',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id'), primary_key=True)
)


class Department(db.Model):
    """Department model"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # MCA, BBA, BCA, BCOM, MBA
    code = db.Column(db.String(10), unique=True, nullable=False)  # MCA, BBA, etc.
    hod_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    programs = db.relationship('Program', backref='department', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Department {self.name}>'


class Program(db.Model):
    """Program/Semester model"""
    __tablename__ = 'programs'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4... up to 4 for MCA, 6 for MBA/BBA/BCA
    academic_year = db.Column(db.String(9), nullable=False)  # 2023-2024
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    courses = db.relationship('Course', backref='program', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('department_id', 'semester', 'academic_year', name='_program_uc'),)
    
    def __repr__(self):
        return f'<Program {self.department.name} Sem {self.semester}>'


class Course(db.Model):
    """Course model"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)  # CS101, DBMS201, etc.
    course_name = db.Column(db.String(150), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    credits = db.Column(db.Integer, default=4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='course', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='course', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('program_id', 'course_code', name='_course_uc'),)
    
    def __repr__(self):
        return f'<Course {self.course_code}>'


class Student(db.Model):
    """Student model"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    registration_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    admission_year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='student_profile')
    department = db.relationship('Department')
    enrollments = db.relationship('Enrollment', backref='student', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Student {self.registration_number}>'


class Enrollment(db.Model):
    """Student enrollment in a course"""
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, dropped, completed
    
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_enrollment_uc'),)
    
    def __repr__(self):
        return f'<Enrollment {self.student_id} - {self.course_id}>'


class ExaminationType(Enum):
    """Types of examinations"""
    INTERNAL = 'internal'
    EXTERNAL = 'external'
    PLACEMENT = 'placement'


class Result(db.Model):
    """Result model - Main result storage"""
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    examination_type = db.Column(db.String(20), nullable=False)  # internal, external, placement
    
    # Internal Exam: CIE (Continuous Internal Evaluation)
    cie_assessment_1 = db.Column(db.Float, default=0)  # Out of 10
    cie_assessment_2 = db.Column(db.Float, default=0)  # Out of 10
    cie_assessment_3 = db.Column(db.Float, default=0)  # Out of 10
    mid_term_marks = db.Column(db.Float, default=0)  # Out of 20
    assignment_marks = db.Column(db.Float, default=0)  # Out of variable
    internal_total = db.Column(db.Float, default=0)  # Out of 40
    
    # External Exam
    external_marks = db.Column(db.Float, default=0)  # Out of 60
    
    # Academic Total (Internal + External) - Out of 100
    academic_total = db.Column(db.Float, default=0)
    pass_fail = db.Column(db.String(10), default='Not Graded')  # Pass, Fail, Not Graded
    
    # Placement Preparation
    dsa_mock_exam = db.Column(db.Float, default=0)
    oops_mock_exam = db.Column(db.Float, default=0)
    dbms_mock_exam = db.Column(db.Float, default=0)
    programming_mock_exam = db.Column(db.Float, default=0)
    aptitude_score = db.Column(db.Float, default=0)
    interview_score = db.Column(db.Float, default=0)
    placement_average = db.Column(db.Float, default=0)
    
    # Grade information
    grade = db.Column(db.String(5), default='')  # A+, A, B+, B, C, D, F
    grade_point = db.Column(db.Float, default=0.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    remarks = db.Column(db.Text, default='')
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', 'examination_type', name='_result_uc'),
    )
    
    def calculate_internal_total(self):
        """Calculate internal marks total (out of 40)"""
        # CIE: 3 assessments × 10 = 30 marks converted to out of 30
        # Mid term: out of 20 (converted to out of 10)
        # Assignment: out of 10
        cie_total = (self.cie_assessment_1 + self.cie_assessment_2 + self.cie_assessment_3) / 3 * 10
        self.internal_total = cie_total + (self.mid_term_marks / 2) + self.assignment_marks
        return self.internal_total
    
    def calculate_academic_total(self):
        """Calculate total academic marks (internal + external out of 100)"""
        self.academic_total = self.internal_total + self.external_marks
        # Check pass/fail (need 40 marks out of 100)
        self.pass_fail = 'Pass' if self.academic_total >= 40 else 'Fail'
        return self.academic_total
    
    def calculate_placement_average(self):
        """Calculate placement preparation average"""
        scores = [self.dsa_mock_exam, self.oops_mock_exam, self.dbms_mock_exam, 
                  self.programming_mock_exam, self.aptitude_score, self.interview_score]
        valid_scores = [s for s in scores if s > 0]
        if valid_scores:
            self.placement_average = sum(valid_scores) / len(valid_scores)
        return self.placement_average
    
    def assign_grade(self):
        """Assign grade based on academic total"""
        if self.academic_total >= 90:
            self.grade = 'A+'
            self.grade_point = 4.0
        elif self.academic_total >= 85:
            self.grade = 'A'
            self.grade_point = 3.7
        elif self.academic_total >= 80:
            self.grade = 'B+'
            self.grade_point = 3.3
        elif self.academic_total >= 75:
            self.grade = 'B'
            self.grade_point = 3.0
        elif self.academic_total >= 70:
            self.grade = 'C+'
            self.grade_point = 2.7
        elif self.academic_total >= 60:
            self.grade = 'C'
            self.grade_point = 2.0
        elif self.academic_total >= 50:
            self.grade = 'D'
            self.grade_point = 1.0
        else:
            self.grade = 'F'
            self.grade_point = 0.0
    
    def __repr__(self):
        return f'<Result {self.student_id} - {self.course_id}>'


class AuditLog(db.Model):
    """Audit log for tracking changes"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.table_name}>'
