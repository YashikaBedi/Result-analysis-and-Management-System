"""
Routes for the Result Management System.
All 5 Blueprints: auth, dashboard, results, analytics, admin.
"""
import os
import csv
import io
from functools import wraps
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, send_file, abort, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from app.models import (
    User, UserRole, Department, Program, Course,
    Student, Enrollment, Result, AcademicCalendar
)
from app.forms import (
    LoginForm, RegistrationForm, InternalExamForm, ExternalExamForm,
    PlacementPrepForm, UpdateProfileForm, CreateDepartmentForm, CreateCourseForm
)
from app.utils import (
    calculate_student_gpa, get_student_statistics,
    get_department_statistics, export_results_to_csv,
    export_results_to_pdf, get_course_analytics
)

# ---------------------------------------------------------------------------
# Helper decorators
# ---------------------------------------------------------------------------

def admin_required(f):
    """Restrict access to admin/hod roles."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated


def faculty_required(f):
    """Restrict access to faculty, admin, or hod."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ('faculty', 'admin'):
            flash('Access denied. Faculty privileges required.', 'error')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated


# ============================================================================
#  AUTH BLUEPRINT
# ============================================================================
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Contact admin.', 'error')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=True)


            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard.home'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/request-reset', methods=['GET', 'POST'])
def request_reset():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = User.query.filter_by(username=username).first()
        if user:
            user.password_reset_requested = True
            db.session.commit()
            flash('Password reset request submitted. An admin will process it.', 'success')
        else:
            flash('Username not found.', 'error')
        return redirect(url_for('auth.login'))
    return render_template('auth/request_reset.html')


@auth_bp.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        if len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        else:
            user.set_password(new_password)
            user.password_reset_requested = False
            db.session.commit()
            flash(f'Password for {user.full_name} has been reset.', 'success')
            return redirect(url_for('admin.dashboard'))
    return render_template('auth/reset_password.html', user=user)


# ============================================================================
#  DASHBOARD BLUEPRINT
# ============================================================================
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


def _build_class_placement_data(students):
    """Compute class-level placement averages."""
    dsa_list, apt_list, int_list = [], [], []
    for s in students:
        p_results = Result.query.filter_by(student_id=s.id, examination_type='placement').all()
        for r in p_results:
            if r.dsa_mock_exam > 0:
                dsa_list.append(r.dsa_mock_exam)
            if r.aptitude_score > 0:
                apt_list.append(r.aptitude_score)
            if r.interview_score > 0:
                int_list.append(r.interview_score)
    return {
        'dsa': round(sum(dsa_list) / len(dsa_list), 1) if dsa_list else 0,
        'aptitude': round(sum(apt_list) / len(apt_list), 1) if apt_list else 0,
        'interview': round(sum(int_list) / len(int_list), 1) if int_list else 0,
    }


def _build_class_internal_external(students):
    """Compute class-level internal and external averages."""
    internals, externals = [], []
    for s in students:
        results = Result.query.filter_by(student_id=s.id, examination_type='internal').all()
        for r in results:
            internals.append(r.internal_total)
            externals.append(r.external_marks)
    ci = round(sum(internals) / len(internals), 1) if internals else 0
    ce = round(sum(externals) / len(externals), 1) if externals else 0
    return ci, ce


def _build_student_data(student):
    """Compute individual student data dict for templates."""
    results = Result.query.filter_by(student_id=student.id, examination_type='internal').all()
    p_results = Result.query.filter_by(student_id=student.id, examination_type='placement').all()

    internal_avg = round(sum(r.internal_total for r in results) / len(results), 1) if results else 0
    external_avg = round(sum(r.external_marks for r in results) / len(results), 1) if results else 0

    # Build subject_data list with all courses
    subject_data = []
    for r in results:
        if r.course:
            subject_data.append({
                'code': r.course.course_code,
                'subject': r.course.course_name,
                'total': r.academic_total,
                'grade': r.grade,
                'status': r.pass_fail,
            })

    # Build placement_data dict
    placement_data = {}
    if p_results:
        pr = p_results[0]
        placement_data = {
            'dsa': pr.dsa_mock_exam or 0,
            'oops': pr.oops_mock_exam or 0,
            'dbms': pr.dbms_mock_exam or 0,
            'programming': pr.programming_mock_exam or 0,
            'aptitude': pr.aptitude_score or 0,
            'interview': pr.interview_score or 0,
            'average': pr.placement_average or 0,
        }

    return {
        'internal': internal_avg,
        'external': external_avg,
        'p': {
            'dsa': placement_data.get('dsa', 0),
            'aptitude': placement_data.get('aptitude', 0),
            'interview': placement_data.get('interview', 0),
        },
        'subject_data': subject_data,
        'placement_data': placement_data,
    }


@dashboard_bp.route('/')
@login_required
def home():
    role = current_user.role
    
    # Academic Pulse: Fetch upcoming events
    today = datetime.utcnow().date()
    upcoming_events = AcademicCalendar.query.filter(AcademicCalendar.start_date >= today).order_by(AcademicCalendar.start_date.asc()).limit(5).all()

    if role == 'student':
        # Student dashboard
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student:
            return redirect(url_for('dashboard.complete_student_profile'))

        stats = get_student_statistics(student.id) or {
            'total_courses': 0, 'passed_courses': 0, 'failed_courses': 0,
            'average_marks': 0, 'gpa': 0, 'placement_average': 0,
        }

        results = Result.query.filter_by(student_id=student.id, examination_type='internal').all()
        all_students = Student.query.filter_by(department_id=student.department_id).all()

        class_p = _build_class_placement_data(all_students)
        class_internal, class_external = _build_class_internal_external(all_students)
        student_data = _build_student_data(student)

        # Student needs a program reference for semester display
        # Attach first enrolled program
        enrollment = Enrollment.query.filter_by(student_id=student.id).first()
        if enrollment and enrollment.course:
            student.program = enrollment.course.program
        else:
            # Fallback: create a mock program object
            class MockProgram:
                semester = 1
            student.program = MockProgram()

        # Simple AI Projection: Based on internal average
        projection = None
        if stats and stats.get('average_marks', 0) > 0:
            avg = stats['average_marks']
            if avg >= 85: projected_grade = 'A+'
            elif avg >= 75: projected_grade = 'A'
            elif avg >= 65: projected_grade = 'B+'
            elif avg >= 55: projected_grade = 'B'
            elif avg >= 40: projected_grade = 'C'
            else: projected_grade = 'F'
            
            # Heuristic: Expected final based on current average + slight improvement
            expected_total = min(100, avg * 1.1) 
            
            projection = {
                'grade': projected_grade,
                'confidence': 'High' if len(results) > 4 else 'Developing',
                'score': round(expected_total, 1),
                'message': "Keep up the consistent effort!" if avg > 60 else "Focus more on upcoming examinations."
            }

        return render_template('dashboard/student_home.html',
                               student=student, stats=stats, results=results,
                               class_p=class_p, class_internal=class_internal,
                               class_external=class_external, student_data=student_data,
                               upcoming_events=upcoming_events,
                               projection=projection)

    elif role in ('faculty',):
        # Faculty dashboard
        courses = Course.query.filter_by(faculty_id=current_user.id).all()

        # Gather all students across assigned courses
        enrolled_student_ids = set()
        for course in courses:
            for e in course.enrollments:
                enrolled_student_ids.add(e.student_id)
        students_count = len(enrolled_student_ids)

        all_students = Student.query.filter(Student.id.in_(enrolled_student_ids)).all() if enrolled_student_ids else []

        class_p = _build_class_placement_data(all_students)
        class_internal, class_external = _build_class_internal_external(all_students)

        # Faculty-wide analytics
        faculty_grade_dist = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'F': 0}
        pass_count = 0
        total_results = 0
        
        for s in all_students:
            res = Result.query.filter_by(student_id=s.id, examination_type='internal').all()
            for r in res:
                if r.grade in faculty_grade_dist:
                    faculty_grade_dist[r.grade] += 1
                if r.pass_fail == 'Pass':
                    pass_count += 1
                total_results += 1
        
        overall_pass_rate = round((pass_count / total_results) * 100, 1) if total_results > 0 else 0

        # Handle per-student selection
        selected_student = None
        student_data = None
        student_id = request.args.get('student_id', type=int)
        if student_id:
            selected_student = Student.query.get(student_id)
            if selected_student:
                student_data = _build_student_data(selected_student)

        return render_template('dashboard/faculty_home.html',
                               courses=courses, students_count=students_count,
                               all_students=all_students, selected_student=selected_student,
                               student_data=student_data,
                               class_p=class_p, class_internal=class_internal,
                               class_external=class_external,
                               faculty_grade_dist=faculty_grade_dist,
                               overall_pass_rate=overall_pass_rate,
                               upcoming_events=upcoming_events)

    else:
        # Admin / HOD dashboard redirect to the dedicated admin route
        return redirect(url_for('admin.dashboard'))


@dashboard_bp.route('/profile')
@login_required
def profile():
    return render_template('dashboard/profile.html')


@dashboard_bp.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_student_profile():
    if current_user.role != 'student':
        return redirect(url_for('dashboard.home'))

    # Check if already has profile
    existing = Student.query.filter_by(user_id=current_user.id).first()
    if existing:
        return redirect(url_for('dashboard.home'))

    departments = Department.query.all()

    if request.method == 'POST':
        reg_num = request.form.get('registration_number', '').strip()
        dept_id = request.form.get('department_id', type=int)
        admission_year = request.form.get('admission_year', type=int)

        if not reg_num or not dept_id or not admission_year:
            flash('All fields are required.', 'error')
        elif Student.query.filter_by(registration_number=reg_num).first():
            flash('Registration number already exists.', 'error')
        else:
            student = Student(
                user_id=current_user.id,
                registration_number=reg_num,
                department_id=dept_id,
                admission_year=admission_year
            )
            db.session.add(student)
            db.session.commit()
            flash('Profile completed successfully!', 'success')
            return redirect(url_for('dashboard.home'))

    return render_template('dashboard/complete_student_profile.html', departments=departments)


# ============================================================================
#  RESULTS BLUEPRINT
# ============================================================================
results_bp = Blueprint('results', __name__, url_prefix='/results')


@results_bp.route('/')
@results_bp.route('/view')
@login_required
def view_results():
    role = current_user.role
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    exam_type = request.args.get('exam_type', '').strip()

    query = Result.query.join(Student).join(User, Student.user_id == User.id)

    # Role-based data filtering
    if role == 'student':
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student:
            flash('Please complete your student profile first.', 'warning')
            return redirect(url_for('dashboard.complete_student_profile'))
        query = query.filter(Result.student_id == student.id)
    elif role == 'faculty':
        # Faculty see students they teach (internal results) or placement results
        query = query.outerjoin(Course).filter(
            (Course.faculty_id == current_user.id) | (Result.examination_type == 'placement')
        )
    
    # Apply search filters
    if search_query:
        query = query.filter(
            (Student.registration_number.ilike(f'%{search_query}%')) |
            (User.full_name.ilike(f'%{search_query}%'))
        )
    
    if exam_type:
        query = query.filter(Result.examination_type == exam_type)

    results = query.order_by(Result.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('results/view_results.html', 
                           results=results, 
                           search=search_query, 
                           exam_type=exam_type)


@results_bp.route('/add-marks', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_marks():
    # Permission check: Admin can do anything; Faculty can only add to their subjects
    if current_user.role == 'admin':
        courses = Course.query.all()
    else:
        courses = Course.query.filter_by(faculty_id=current_user.id).all()

    if request.method == 'POST':
        upload_type = request.form.get('upload_type', '')
        course_id = request.form.get('course_id', type=int)
        file = request.files.get('file')

        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'error')
            return redirect(url_for('results.add_marks'))

        try:
            stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
            reader = csv.DictReader(stream)
            count = 0

            for row in reader:
                reg_num = row.get('registration_number', '').strip()
                student = Student.query.filter_by(registration_number=reg_num).first()
                if not student:
                    continue

                if upload_type == 'internal':
                    # Verify faculty has permission for this course
                    course = Course.query.get(course_id)
                    # Permission check
                    if current_user.role != 'admin' and course.faculty_id != current_user.id:
                        flash(f'Unauthorized: You are not the allotted faculty for {course.course_code}.', 'error')
                        return redirect(url_for('results.add_marks'))

                    result = Result.query.filter_by(
                        student_id=student.id, course_id=course_id,
                        examination_type='internal'
                    ).first()
                    if not result:
                        result = Result(
                            student_id=student.id, course_id=course_id,
                            examination_type='internal', recorded_by=current_user.id
                        )
                        db.session.add(result)

                    result.cie_1 = float(row.get('cie1', 0) or 0)
                    result.cie_2 = float(row.get('cie2', 0) or 0)
                    result.cie_3 = float(row.get('cie3', 0) or 0)
                    result.internal_exam_1 = float(row.get('ie1', row.get('mid_term', 0)) or 0)
                    result.internal_exam_2 = float(row.get('ie2', 0) or 0)
                    result.assignment_marks = float(row.get('assignment', 0) or 0)
                    result.practical_file_marks = float(row.get('pract_file', 0) or 0)
                    result.internal_practical_marks = float(row.get('pract_exam', 0) or 0)
                    result.remarks = row.get('remarks', '')
                    result.calculate_internal_total()
                    result.calculate_academic_total()
                    result.assign_grade()

                elif upload_type == 'external':
                    result = Result.query.filter_by(
                        student_id=student.id, course_id=course_id,
                        examination_type='internal'
                    ).first()
                    if result:
                        result.external_marks = float(row.get('external_marks', 0) or 0)
                        result.calculate_academic_total()
                        result.assign_grade()

                elif upload_type == 'placement':
                    result = Result.query.filter_by(
                        student_id=student.id, examination_type='placement'
                    ).first()
                    if not result:
                        result = Result(
                            student_id=student.id, examination_type='placement',
                            recorded_by=current_user.id
                        )
                        db.session.add(result)

                    result.dsa_mock_exam = float(row.get('dsa', 0) or 0)
                    result.oops_mock_exam = float(row.get('oops', 0) or 0)
                    result.dbms_mock_exam = float(row.get('dbms', 0) or 0)
                    result.programming_mock_exam = float(row.get('programming', 0) or 0)
                    result.aptitude_score = float(row.get('aptitude', 0) or 0)
                    result.interview_score = float(row.get('interview', 0) or 0)
                    result.remarks = row.get('remarks', '')
                    result.calculate_placement_average()

                count += 1

            db.session.commit()
            flash(f'Successfully processed {count} records via {upload_type} upload.', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing CSV: {str(e)}', 'error')

        return redirect(url_for('results.add_marks'))

    return render_template('results/add_marks.html', courses=courses)


@results_bp.route('/add-internal', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_internal_marks():
    form = InternalExamForm()
    if current_user.role == 'admin':
        form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}") for c in Course.query.all()]
    else:
        form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}")
                                  for c in Course.query.filter_by(faculty_id=current_user.id).all()]

    if form.validate_on_submit():
        # Permission check
        course = Course.query.get(form.course_id.data)
        if current_user.role != 'admin' and course.faculty_id != current_user.id:
            flash('Unauthorized: You are not the allotted faculty for this course.', 'error')
            return redirect(url_for('results.add_internal_marks'))

        student = Student.query.filter_by(registration_number=form.student_id.data).first()
        if not student:
            flash('Student not found.', 'error')
        else:
            result = Result.query.filter_by(
                student_id=student.id, course_id=form.course_id.data,
                examination_type='internal'
            ).first()
            if not result:
                result = Result(
                    student_id=student.id, course_id=form.course_id.data,
                    examination_type='internal', recorded_by=current_user.id
                )
                db.session.add(result)

            result.cie_1 = form.cie_assessment_1.data
            result.cie_2 = form.cie_assessment_2.data
            result.cie_3 = form.cie_assessment_3.data
            result.internal_exam_1 = form.mid_term_marks_1.data
            result.internal_exam_2 = form.mid_term_marks_2.data
            result.assignment_marks = form.assignment_marks.data
            result.practical_file_marks = form.practical_file_marks.data or 0
            result.internal_practical_marks = form.internal_practical_marks.data or 0
            result.remarks = form.remarks.data or ''
            result.calculate_internal_total()
            result.calculate_academic_total()
            result.assign_grade()
            db.session.commit()
            flash('Internal marks saved successfully!', 'success')
            return redirect(url_for('results.add_internal_marks'))

    return render_template('results/add_internal_marks.html', form=form)


@results_bp.route('/add-external', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_external_marks():
    form = ExternalExamForm()
    if current_user.role == 'admin':
        form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}") for c in Course.query.all()]
    else:
        form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}")
                                  for c in Course.query.filter_by(faculty_id=current_user.id).all()]

    if form.validate_on_submit():
        # Permission check
        course = Course.query.get(form.course_id.data)
        if current_user.role != 'admin' and course.faculty_id != current_user.id:
            flash('Unauthorized: You are not the allotted faculty for this course.', 'error')
            return redirect(url_for('results.add_external_marks'))

        student = Student.query.filter_by(registration_number=form.student_id.data).first()
        if not student:
            flash('Student not found.', 'error')
        else:
            result = Result.query.filter_by(
                student_id=student.id, course_id=form.course_id.data,
                examination_type='internal'
            ).first()
            if result:
                result.external_marks = form.external_marks.data
                result.calculate_academic_total()
                result.assign_grade()
                db.session.commit()
                flash('External marks saved!', 'success')
            else:
                flash('Internal marks must be entered first.', 'error')
            return redirect(url_for('results.add_external_marks'))

    return render_template('results/add_external_marks.html', form=form)


@results_bp.route('/add-placement', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_placement_scores():
    form = PlacementPrepForm()

    if form.validate_on_submit():
        student = Student.query.filter_by(registration_number=form.student_id.data).first()
        if not student:
            flash('Student not found.', 'error')
        else:
            result = Result.query.filter_by(
                student_id=student.id, examination_type='placement'
            ).first()
            if not result:
                result = Result(
                    student_id=student.id, examination_type='placement',
                    recorded_by=current_user.id
                )
                db.session.add(result)

            result.dsa_mock_exam = form.dsa_mock_exam.data or 0
            result.oops_mock_exam = form.oops_mock_exam.data or 0
            result.dbms_mock_exam = form.dbms_mock_exam.data or 0
            result.programming_mock_exam = form.programming_mock_exam.data or 0
            result.aptitude_score = form.aptitude_score.data or 0
            result.interview_score = form.interview_score.data or 0
            result.remarks = form.remarks.data or ''
            result.calculate_placement_average()
            db.session.commit()
            flash('Placement scores saved!', 'success')
            return redirect(url_for('results.add_placement_scores'))

    return render_template('results/add_placement_scores.html', form=form)




@results_bp.route('/export-csv')
@login_required
@faculty_required
def export_csv():
    try:
        output = export_results_to_csv()
        return send_file(output, mimetype='text/csv',
                         as_attachment=True, download_name='results_export.csv')
    except Exception as e:
        flash(f'Export failed: {str(e)}', 'error')
        return redirect(url_for('results.view_results'))


@results_bp.route('/export-pdf')
@login_required
@faculty_required
def export_pdf():
    try:
        output = export_results_to_pdf()
        return send_file(output, mimetype='application/pdf',
                         as_attachment=True, download_name='results_export.pdf')
    except Exception as e:
        flash(f'Export failed: {str(e)}', 'error')
        return redirect(url_for('results.view_results'))


# ============================================================================
#  ANALYTICS BLUEPRINT
# ============================================================================
analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/hub')
@login_required
def analysis_hub():
    # ── Role-based scoping ──────────────────────────────────────────────────
    # Initialize variables that may not be set for all roles
    trend_labels, trend_values = [], []

    if current_user.role == 'student':
        student = Student.query.filter_by(user_id=current_user.id).first()
        students = [student] if student else []
        if student:
            course_ids = [e.course_id for e in Enrollment.query.filter_by(student_id=student.id).all()]
            courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []
        else:
            courses = []
    elif current_user.role == 'faculty':
        courses = Course.query.filter_by(faculty_id=current_user.id).all()
        student_ids = set()
        for c in courses:
            for e in c.enrollments:
                student_ids.add(e.student_id)
        students = Student.query.filter(Student.id.in_(student_ids)).all() if student_ids else []
    else:  # admin
        students = Student.query.all()
        courses = Course.query.all()

    departments = Department.query.all()

    # ── Selection preview ───────────────────────────────────────────────────
    selected_student = None
    selected_course = None
    student_preview = None
    course_preview = None

    student_id = request.args.get('student_id', type=int)
    course_id  = request.args.get('course_id',  type=int)

    if student_id:
        selected_student = Student.query.get(student_id)
        if selected_student:
            student_preview = _build_student_data(selected_student)
            student_preview['stats'] = get_student_statistics(selected_student.id) or {
                'total_courses': 0, 'passed_courses': 0, 'failed_courses': 0,
                'average_marks': 0, 'gpa': 0, 'placement_average': 0,
            }
            student_preview['gpa'] = calculate_student_gpa(selected_student.id)
            # Enrich subject_data for hub table
            all_results = Result.query.filter_by(student_id=selected_student.id,
                                                  examination_type='internal').all()
            rich = []
            for r in all_results:
                if r.course:
                    rich.append({
                        'code':     r.course.course_code,
                        'subject':  r.course.course_name,
                        'total':    round(r.academic_total or 0, 1),
                        'grade':    r.grade or '—',
                        'status':   r.pass_fail or 'Not Graded',
                    })
            student_preview['subject_data'] = rich

            # Historical trend
            historical_trends = {}
            for r in Result.query.filter_by(student_id=selected_student.id).all():
                if r.course and r.course.program and r.academic_total:
                    sem = f"Sem {r.course.program.semester}"
                    if sem not in historical_trends:
                        historical_trends[sem] = {'total': 0, 'count': 0}
                    historical_trends[sem]['total'] += r.academic_total
                    historical_trends[sem]['count'] += 1
            trend_labels = sorted(historical_trends.keys())
            trend_values = [round(historical_trends[l]['total'] / historical_trends[l]['count'], 1)
                            for l in trend_labels]
        else:
            trend_labels, trend_values = [], []
    else:
        trend_labels, trend_values = [], []

    if course_id:
        selected_course = Course.query.get(course_id)
        if selected_course:
            results = Result.query.filter_by(course_id=course_id, examination_type='internal').all()
            totals = [r.academic_total for r in results if r.academic_total is not None]
            passes = sum(1 for r in results if r.pass_fail == 'Pass')
            grade_breakdown = {}
            for r in results:
                key = r.grade or 'N/A'
                grade_breakdown[key] = grade_breakdown.get(key, 0) + 1
            course_preview = {
                'course':          selected_course,
                'average':         round(sum(totals) / len(totals), 1) if totals else 0,
                'pass_rate':       round((passes / len(results)) * 100, 1) if results else 0,
                'enrolled':        len(selected_course.enrollments),
                'grade_breakdown': grade_breakdown,
            }

    # ── Faculty-specific aggregates ─────────────────────────────────────────
    faculty_grade_dist = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'F': 0}
    pass_count = 0
    total_results = 0
    class_internal, class_external = 0.0, 0.0

    if current_user.role == 'faculty':
        int_list, ext_list = [], []
        for s in students:
            for r in Result.query.filter_by(student_id=s.id, examination_type='internal').all():
                if r.course and r.course.faculty_id == current_user.id:
                    if r.grade in faculty_grade_dist:
                        faculty_grade_dist[r.grade] += 1
                    if r.pass_fail == 'Pass':
                        pass_count += 1
                    total_results += 1
                    int_list.append(r.internal_total or 0)
                    ext_list.append(r.external_marks or 0)
        class_internal = round(sum(int_list) / len(int_list), 1) if int_list else 0
        class_external = round(sum(ext_list) / len(ext_list), 1) if ext_list else 0

    overall_pass_rate = round((pass_count / total_results) * 100, 1) if total_results > 0 else 0

    # ── Admin-specific: college-wide grade distribution ─────────────────────
    college_grade_dist = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'F': 0}
    if current_user.role == 'admin':
        for r in Result.query.filter_by(examination_type='internal').all():
            key = r.grade or 'F'
            if key in college_grade_dist:
                college_grade_dist[key] += 1

    # ── Student self-view extras ────────────────────────────────────────────
    if current_user.role == 'student' and students and not selected_student:
        # Auto-select the current student
        selected_student = students[0]
        student_preview = _build_student_data(selected_student)
        student_preview['stats'] = get_student_statistics(selected_student.id) or {
            'total_courses': 0, 'passed_courses': 0, 'failed_courses': 0,
            'average_marks': 0, 'gpa': 0, 'placement_average': 0,
        }
        student_preview['gpa'] = calculate_student_gpa(selected_student.id)
        all_results = Result.query.filter_by(student_id=selected_student.id,
                                              examination_type='internal').all()
        student_preview['subject_data'] = [{
            'code':    r.course.course_code if r.course else '—',
            'subject': r.course.course_name if r.course else '—',
            'total':   round(r.academic_total or 0, 1),
            'grade':   r.grade or '—',
            'status':  r.pass_fail or 'Not Graded',
        } for r in all_results if r.course]

        # Historical trend
        historical_trends = {}
        for r in Result.query.filter_by(student_id=selected_student.id).all():
            if r.course and r.course.program and r.academic_total:
                sem = f"Sem {r.course.program.semester}"
                if sem not in historical_trends:
                    historical_trends[sem] = {'total': 0, 'count': 0}
                historical_trends[sem]['total'] += r.academic_total
                historical_trends[sem]['count'] += 1
        trend_labels = sorted(historical_trends.keys())
        trend_values = [round(historical_trends[l]['total'] / historical_trends[l]['count'], 1)
                        for l in trend_labels]


    return render_template('analytics/hub.html',
                           students=students, courses=courses, departments=departments,
                           selected_student=selected_student, student_preview=student_preview,
                           selected_course=selected_course, course_preview=course_preview,
                           trend_labels=trend_labels, trend_values=trend_values,
                           faculty_grade_dist=faculty_grade_dist,
                           class_internal=class_internal, class_external=class_external,
                           overall_pass_rate=overall_pass_rate,
                           college_grade_dist=college_grade_dist)




@analytics_bp.route('/student/<int:student_id>')
@login_required
def student_analytics(student_id):
    student = Student.query.get_or_404(student_id)
    stats = get_student_statistics(student.id)
    gpa = calculate_student_gpa(student.id)

    # Build subject_data list for template
    all_results = Result.query.filter_by(student_id=student.id).all()
    subject_data = []
    historical_trends = {} # {semester: {'avg': X, 'count': Y}}
    
    for r in all_results:
        if r.examination_type == 'internal' and r.course:
            subject_data.append({
                'code': r.course.course_code,
                'subject': r.course.course_name,
                'cie_1': r.cie_1,
                'cie_2': r.cie_2,
                'cie_3': r.cie_3,
                'ie_1': r.internal_exam_1,
                'ie_2': r.internal_exam_2,
                'assignment': r.assignment_marks,
                'practical_file': r.practical_file_marks,
                'practical_internal': r.internal_practical_marks,
                'internal_total': r.internal_total,
                'external': r.external_marks,
                'total': r.academic_total,
                'grade': r.grade,
                'status': r.pass_fail,
                'semester': r.course.program.semester if r.course.program else 'N/A'
            })
        
        # Calculate historical trends for line chart
        if r.course and r.course.program:
            sem = f"Sem {r.course.program.semester}"
            if sem not in historical_trends:
                historical_trends[sem] = {'internal': 0, 'external': 0, 'count': 0}
            historical_trends[sem]['internal'] += (r.internal_total or 0)
            historical_trends[sem]['external'] += (r.external_marks or 0)
            historical_trends[sem]['count'] += 1

    # Format trends for Chart.js
    trend_labels = sorted(historical_trends.keys())
    trend_internal = [round(historical_trends[l]['internal'] / historical_trends[l]['count'], 1) for l in trend_labels]
    trend_external = [round(historical_trends[l]['external'] / historical_trends[l]['count'], 1) for l in trend_labels]

    # Build placement data
    p_result = Result.query.filter_by(student_id=student.id, examination_type='placement').first()
    placement_data = None
    if p_result:
        placement_data = {
            'dsa': p_result.dsa_mock_exam,
            'oops': p_result.oops_mock_exam,
            'dbms': p_result.dbms_mock_exam,
            'programming': p_result.programming_mock_exam,
            'aptitude': p_result.aptitude_score,
            'interview': p_result.interview_score,
            'average': p_result.placement_average,
        }

    return render_template('analytics/student_analytics.html',
                           student=student, stats=stats, gpa=gpa,
                           subject_data=subject_data, placement_data=placement_data,
                           trend_labels=trend_labels, trend_internal=trend_internal, trend_external=trend_external)

@analytics_bp.route('/report/<int:student_id>')
@login_required
def performance_report(student_id):
    # Ensure students can only see their own report, or admin/faculty can see any
    if current_user.role == 'student':
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student or student.id != student_id:
            flash('Unauthorized access!', 'error')
            return redirect(url_for('dashboard.home'))
    
    student = Student.query.get_or_404(student_id)
    all_results = Result.query.filter_by(student_id=student.id, examination_type='internal').all()
    stats = get_student_statistics(student.id)
    gpa = calculate_student_gpa(student.id)
    
    # Calculate semester-wise totals
    semesters = {}
    for r in all_results:
        sem = r.course.program.semester if r.course and r.course.program else 1
        if sem not in semesters:
            semesters[sem] = []
        semesters[sem].append(r)
    
    sorted_sems = sorted(semesters.keys())
    
    return render_template('analytics/performance_report.html',
                           student=student, 
                           semesters=semesters, 
                           sorted_sems=sorted_sems,
                           stats=stats, 
                           gpa=gpa)


@analytics_bp.route('/subject/<int:course_id>')
@login_required
def subject_analytics(course_id):
    course = Course.query.get_or_404(course_id)
    results = Result.query.filter_by(course_id=course_id, examination_type='internal').all()

    if not results:
        analytics = {
            'total': 0, 'average': 0, 'highest': 0, 'lowest': 0,
            'pass_count': 0, 'fail_count': 0, 'pass_rate': 0,
        }
        grade_dist = {}
        cie_avgs = {}
        top_10 = []
        sibling_data = None
        return render_template('analytics/subject_analytics.html',
                               course=course, analytics=analytics, results=results,
                               grade_dist=grade_dist, cie_avgs=cie_avgs,
                               top_10=top_10, sibling_data=sibling_data)

    totals = [r.academic_total for r in results]
    pass_count = len([r for r in results if r.pass_fail == 'Pass'])
    fail_count = len(results) - pass_count

    analytics = {
        'total': len(results),
        'average': round(sum(totals) / len(totals), 1),
        'highest': round(max(totals), 1),
        'lowest': round(min(totals), 1),
        'pass_count': pass_count,
        'fail_count': fail_count,
        'pass_rate': round((pass_count / len(results)) * 100, 1),
    }

    # Grade distribution
    grade_dist = {}
    for r in results:
        g = r.grade or 'N/A'
        grade_dist[g] = grade_dist.get(g, 0) + 1

    # CIE averages
    cie_avgs = {
        'CIE-1': round(sum(r.cie_1 for r in results) / len(results), 1),
        'CIE-2': round(sum(r.cie_2 for r in results) / len(results), 1),
        'CIE-3': round(sum(r.cie_3 for r in results) / len(results), 1),
        'IE-1': round(sum(r.internal_exam_1 for r in results) / len(results), 1),
        'IE-2': round(sum(r.internal_exam_2 for r in results) / len(results), 1),
        'Assignment': round(sum(r.assignment_marks for r in results) / len(results), 1),
    }

    # Top 10
    top_10 = sorted(results, key=lambda r: r.academic_total, reverse=True)[:10]

    # Sibling section comparison
    sibling_data = None
    other_section = 'B' if course.section == 'A' else 'A'
    sibling_course = Course.query.filter_by(
        course_code=course.course_code,
        program_id=course.program_id,
        section=other_section
    ).first()
    
    if sibling_course:
        sib_results = Result.query.filter_by(course_id=sibling_course.id, examination_type='internal').all()
        if sib_results:
            sib_totals = [r.academic_total for r in sib_results]
            sib_pass = len([r for r in sib_results if r.pass_fail == 'Pass'])
            sib_grade_dist = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'F': 0}
            for sr in sib_results:
                if sr.grade in sib_grade_dist:
                    sib_grade_dist[sr.grade] += 1
            
            sibling_data = {
                'section': other_section,
                'average': round(sum(sib_totals) / len(sib_totals), 1),
                'pass_rate': round((sib_pass / len(sib_results)) * 100, 1),
                'count': len(sib_results),
                'grade_dist': sib_grade_dist
            }

    return render_template('analytics/subject_analytics.html',
                           course=course, analytics=analytics, results=results,
                           grade_dist=grade_dist, cie_avgs=cie_avgs,
                           top_10=top_10, sibling_data=sibling_data)


@analytics_bp.route('/placement')
@login_required
@faculty_required
def placement_analytics():
    placement_results = Result.query.filter_by(examination_type='placement').all()

    if not placement_results:
        empty_avgs = {'DSA': 0, 'OOP': 0, 'DBMS': 0, 'Programming': 0, 'Aptitude': 0, 'Interview': 0}
        return render_template('analytics/placement_analytics.html',
                               skill_avgs=empty_avgs, placement_results=[],
                               top_placed=[], buckets={})

    skill_avgs = {
        'DSA': round(sum(r.dsa_mock_exam for r in placement_results) / len(placement_results), 1),
        'OOP': round(sum(r.oops_mock_exam for r in placement_results) / len(placement_results), 1),
        'DBMS': round(sum(r.dbms_mock_exam for r in placement_results) / len(placement_results), 1),
        'Programming': round(sum(r.programming_mock_exam for r in placement_results) / len(placement_results), 1),
        'Aptitude': round(sum(r.aptitude_score for r in placement_results) / len(placement_results), 1),
        'Interview': round(sum(r.interview_score for r in placement_results) / len(placement_results), 1),
    }

    top_placed = sorted(placement_results, key=lambda r: r.placement_average, reverse=True)[:10]

    # Score distribution buckets
    buckets = {'90-100': 0, '75-89': 0, '60-74': 0, '40-59': 0, '0-39': 0}
    for r in placement_results:
        avg = r.placement_average
        if avg >= 90:
            buckets['90-100'] += 1
        elif avg >= 75:
            buckets['75-89'] += 1
        elif avg >= 60:
            buckets['60-74'] += 1
        elif avg >= 40:
            buckets['40-59'] += 1
        else:
            buckets['0-39'] += 1

    return render_template('analytics/placement_analytics.html',
                           skill_avgs=skill_avgs, placement_results=placement_results,
                           top_placed=top_placed, buckets=buckets)


# ============================================================================
#  ADMIN BLUEPRINT
# ============================================================================
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def get_department_ranking():
    """Compute department ranking and pass rate for admin dashboards."""
    dept_stats = []
    departments = Department.query.all()
    for dept in departments:
        students = Student.query.filter_by(department_id=dept.id).all()
        if not students:
            dept_stats.append({
                'name': dept.name,
                'avg_score': 0,
                'pass_rate': 0,
                'student_count': 0,
            })
            continue

        student_ids = [student.id for student in students]
        all_results = Result.query.filter(
            Result.student_id.in_(student_ids),
            Result.examination_type == 'internal'
        ).all()

        if all_results:
            avg = round(sum(r.academic_total for r in all_results) / len(all_results), 1)
            passed = len([r for r in all_results if r.pass_fail == 'Pass'])
            rate = round((passed / len(all_results)) * 100, 1)
        else:
            avg, rate = 0, 0

        dept_stats.append({
            'name': dept.name,
            'avg_score': avg,
            'pass_rate': rate,
            'student_count': len(students),
        })

    dept_stats.sort(key=lambda x: x['avg_score'], reverse=True)
    return dept_stats


def get_top_students(limit=5):
    """Fetch top students based on cumulative average across all internal exams"""
    all_students = Student.query.all()
    rankings = []
    
    for student in all_students:
        results = Result.query.filter_by(student_id=student.id, examination_type='internal').all()
        if results:
            avg = sum(r.academic_total for r in results) / len(results)
            rankings.append({
                'name': student.user.full_name,
                'reg_no': student.registration_number,
                'avg': round(avg, 1),
                'dept': student.department.name if student.department else 'N/A'
            })
    
    rankings.sort(key=lambda x: x['avg'], reverse=True)
    return rankings[:limit]


def get_faculty_ranking(limit=5):
    """Compute faculty rankings based on the average academic total of their allotted courses."""
    faculties = User.query.filter_by(role='faculty').all()
    stats = []
    
    for f in faculties:
        courses = Course.query.filter_by(faculty_id=f.id).all()
        if not courses:
            continue
            
        course_ids = [c.id for c in courses]
        results = Result.query.filter(Result.course_id.in_(course_ids), Result.examination_type == 'internal').all()
        
        if results:
            avg = sum(r.academic_total for r in results) / len(results)
            passed = len([r for r in results if r.pass_fail == 'Pass'])
            rate = (passed / len(results)) * 100
            
            stats.append({
                'name': f.full_name,
                'avg': round(avg, 1),
                'pass_rate': round(rate, 1),
                'courses': len(courses)
            })
            
    stats.sort(key=lambda x: x['avg'], reverse=True)
    return stats[:limit]


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    try:
        total_users = User.query.count()
        total_students = Student.query.count()
        total_departments = Department.query.count()
        total_courses = Course.query.count()
        total_results = Result.query.count()

        # Pending password reset requests
        pending_resets = User.query.filter_by(password_reset_requested=True).all()

        # Department performance leaderboard
        dept_stats = get_department_ranking()

        # College-wide Grade Distribution
        college_grade_dist = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'F': 0}
        all_results = Result.query.filter_by(examination_type='internal').all()
        for r in all_results:
            if r.grade in college_grade_dist:
                college_grade_dist[r.grade] += 1

        # Academic Pulse: Fetch upcoming events
        today = datetime.utcnow().date()
        upcoming_events = AcademicCalendar.query.filter(AcademicCalendar.start_date >= today).order_by(AcademicCalendar.start_date.asc()).limit(5).all()

        # Top 5 students across all departments
        top_students = get_top_students(5)

        # Faculty performance leaderboard
        faculty_stats = get_faculty_ranking(5)

        return render_template('admin/dashboard.html',
                               total_users=total_users, total_students=total_students,
                               total_departments=total_departments, total_courses=total_courses,
                               total_results=total_results,
                               pending_resets=pending_resets,
                               dept_stats=dept_stats, college_grade_dist=college_grade_dist,
                               upcoming_events=upcoming_events,
                               top_students=top_students,
                               faculty_stats=faculty_stats)

    except Exception as e:
        import traceback
        import os
        error_msg = traceback.format_exc()
        with open(os.path.join(os.path.dirname(__file__), 'admin_error.txt'), 'w') as f:
            f.write(f"DEBUG ADMIN DASHBOARD ERROR:\n{error_msg}")
        print(f"DEBUG ADMIN DASHBOARD ERROR:\n{error_msg}", flush=True)
        flash(f"Dashboard Error: {str(e)}", 'error')
        return redirect(url_for('dashboard.home'))



@admin_bp.route('/departments')
@login_required
@admin_required
def manage_departments():
    page = request.args.get('page', 1, type=int)
    departments = Department.query.paginate(page=page, per_page=20, error_out=False)

    # Build subjects_data for each department to show "Subjects and Faculty allotted"
    for dept in departments.items:
        subjects_data = []
        # Get all programs/semesters for this department
        programs = Program.query.filter_by(department_id=dept.id).all()
        for prog in programs:
            courses = Course.query.filter_by(program_id=prog.id).all()
            for course in courses:
                faculty_name = "Not Assigned"
                if course.faculty_id:
                    faculty_user = User.query.get(course.faculty_id)
                    if faculty_user:
                        faculty_name = faculty_user.full_name
                
                enrolled_count = Enrollment.query.filter_by(course_id=course.id).count()
                
                subjects_data.append({
                    'code': course.course_code,
                    'name': course.course_name,
                    'section': course.section,
                    'faculty': faculty_name,
                    'enrolled': enrolled_count,
                    'semester': prog.semester
                })
        # Sort by semester then code
        subjects_data.sort(key=lambda x: (x['semester'], x['code']))
        dept.subjects_data = subjects_data

    return render_template('admin/manage_departments.html', departments=departments)



@admin_bp.route('/departments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_department():
    form = CreateDepartmentForm()
    if form.validate_on_submit():
        if Department.query.filter_by(code=form.code.data).first():
            flash('Department code already exists.', 'error')
        else:
            dept = Department(name=form.name.data, code=form.code.data)
            db.session.add(dept)
            db.session.commit()
            flash(f'Department "{form.name.data}" created successfully!', 'success')
            return redirect(url_for('admin.manage_departments'))
    return render_template('admin/create_department.html', form=form)


@admin_bp.route('/departments/edit/<int:dept_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    form = CreateDepartmentForm(obj=dept)
    if form.validate_on_submit():
        dept.name = form.name.data
        dept.code = form.code.data
        db.session.commit()
        flash(f'Department "{dept.name}" updated successfully!', 'success')
        return redirect(url_for('admin.manage_departments'))
    return render_template('admin/create_department.html', form=form, edit_mode=True)


@admin_bp.route('/departments/delete/<int:dept_id>', methods=['POST'])
@login_required
@admin_required
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    name = dept.name
    db.session.delete(dept)
    db.session.commit()
    flash(f'Department "{name}" and all its programs/courses have been removed.', 'success')
    return redirect(url_for('admin.manage_departments'))


@admin_bp.route('/calendar', methods=['GET'])
@login_required
@admin_required
def view_calendar():
    events = AcademicCalendar.query.order_by(AcademicCalendar.start_date.desc()).all()
    departments = Department.query.all()
    return render_template('admin/calendar.html', events=events, departments=departments)

@admin_bp.route('/calendar/create', methods=['POST'])
@login_required
@admin_required
def create_calendar_event():
    title = request.form.get('title', '').strip()
    event_type = request.form.get('event_type', '').strip()
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    dept_id = request.form.get('department_id')
    description = request.form.get('description', '')

    if title and event_type and start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
            
            event = AcademicCalendar(
                title=title,
                event_type=event_type,
                description=description,
                start_date=start_date,
                end_date=end_date,
                department_id=int(dept_id) if dept_id else None,
                created_by=current_user.id
            )
            db.session.add(event)
            db.session.commit()
            flash('Calendar event added!', 'success')
        except Exception as e:
            flash(f'Error adding event: {str(e)}', 'error')
    else:
        flash('Title, type, and start date are required.', 'error')
    
    return redirect(url_for('admin.view_calendar'))

@admin_bp.route('/calendar/delete/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def delete_calendar_event(event_id):
    event = AcademicCalendar.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event removed from calendar.', 'success')
    return redirect(url_for('admin.view_calendar'))


@admin_bp.route('/calendar/edit/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def edit_calendar_event(event_id):
    event = AcademicCalendar.query.get_or_404(event_id)
    event.title = request.form.get('title', event.title).strip()
    event.event_type = request.form.get('event_type', event.event_type).strip()
    start_date_str = request.form.get('start_date')
    if start_date_str:
        event.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    end_date_str = request.form.get('end_date')
    if end_date_str:
        event.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    event.description = request.form.get('description', event.description)
    db.session.commit()
    flash('Event updated successfully.', 'success')
    return redirect(url_for('admin.view_calendar'))
# REMOVED: User management and audit logs functionality per business requirements
