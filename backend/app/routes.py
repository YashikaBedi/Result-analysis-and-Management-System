from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from app.models import (
    User, Student, Department, Program, Course, Result, Enrollment, UserRole, AuditLog
)
from app.forms import (
    LoginForm, RegistrationForm, InternalExamForm, ExternalExamForm, 
    PlacementPrepForm, UpdateProfileForm, CreateDepartmentForm, CreateCourseForm
)
from app.utils import (
    calculate_student_gpa, get_student_statistics, get_department_statistics,
    export_results_to_csv, export_results_to_pdf, log_audit_action,
    search_results, get_course_analytics, get_grade_distribution
)
from functools import wraps
from datetime import datetime

# Create Blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
results_bp = Blueprint('results', __name__, url_prefix='/results')
analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ============= DECORATORS =============
def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'hod']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated_function


def faculty_required(f):
    """Decorator to require faculty role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['faculty', 'admin', 'hod']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated_function


# ============= AUTHENTICATION ROUTES =============
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Contact administrator.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        log_audit_action(user.id, 'LOGIN', 'users', user.id)
        
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('dashboard.home'))
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Log the user in automatically
        login_user(user)
        
        # If student, redirect to complete student profile
        if form.role.data == 'student':
            flash('Registration successful! Please complete your student profile.', 'success')
            return redirect(url_for('dashboard.complete_student_profile'))
        
        # For faculty/admin, redirect to dashboard
        flash('Registration successful! Welcome to the system.', 'success')
        return redirect(url_for('dashboard.home'))
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    log_audit_action(current_user.id, 'LOGOUT', 'users', current_user.id)
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


# ============= DASHBOARD ROUTES =============
@dashboard_bp.route('/')
@login_required
def home():
    """Dashboard home"""
    if current_user.role == 'student':
        # Student dashboard
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student:
            return redirect(url_for('dashboard.complete_student_profile'))
            
        stats = get_student_statistics(student.id)
        results = Result.query.filter_by(student_id=student.id).all()
        
        # --- CLASS BENCHMARKS ---
        # Get averages for the courses this student is enrolled in
        enrolled_course_ids = [e.course_id for e in student.enrollments]
        class_internal = 0
        class_external = 0
        class_p = {'dsa': 0, 'aptitude': 0, 'interview': 0}

        if enrolled_course_ids:
            academic_results = Result.query.filter(Result.course_id.in_(enrolled_course_ids), Result.examination_type == 'internal').all()
            if academic_results:
                class_internal = sum([r.internal_total for r in academic_results]) / len(academic_results)
                ext = [r.external_marks for r in academic_results if r.external_marks > 0]
                class_external = sum(ext) / len(ext) if ext else 0

            # Placement averages for entire department (benchmark)
            p_results = Result.query.join(Student).filter(Student.department_id == student.department_id, Result.examination_type == 'placement').all()
            if p_results:
                class_p['dsa'] = sum([r.dsa_mock_exam for r in p_results]) / len(p_results)
                class_p['aptitude'] = sum([r.aptitude_score for r in p_results]) / len(p_results)
                class_p['interview'] = sum([r.interview_score for r in p_results]) / len(p_results)

        # Personal Placement Data
        s_p = Result.query.filter_by(student_id=student.id, examination_type='placement').first()
        
        s_internal_list = [r for r in results if r.examination_type == 'internal']
        s_external_list = [r for r in results if r.examination_type == 'internal' and r.external_marks > 0]
        
        student_data = {
            'internal': sum([r.internal_total for r in s_internal_list]) / len(s_internal_list) if s_internal_list else 0,
            'external': sum([r.external_marks for r in s_external_list]) / len(s_external_list) if s_external_list else 0,
            'p': {
                'dsa': s_p.dsa_mock_exam if s_p else 0,
                'aptitude': s_p.aptitude_score if s_p else 0,
                'interview': s_p.interview_score if s_p else 0
            }
        }

        return render_template('dashboard/student_home.html', 
                             stats=stats, 
                             results=results, 
                             student=student,
                             student_data=student_data,
                             class_p=class_p,
                             class_internal=round(class_internal, 2),
                             class_external=round(class_external, 2))
    
    elif current_user.role in ['faculty', 'hod', 'admin']:
        # Faculty dashboard
        if current_user.role == 'admin':
            courses = Course.query.all()
        else:
            courses = Course.query.filter_by(faculty_id=current_user.id).all()
            
        course_ids = [c.id for c in courses]
        
        # Get all students enrolled in these courses for the selection dropdown
        students_query = Student.query.join(Enrollment).filter(Enrollment.course_id.in_(course_ids)).distinct() if course_ids else Student.query.filter_by(id=-1)
        all_students = students_query.order_by(Student.registration_number).all()
        students_count = len(all_students)
        
        # GET params for specific student
        selected_student_id = request.args.get('student_id', type=int)
        selected_student = Student.query.get(selected_student_id) if selected_student_id else None

        # --- CLASS ANALYTICS ---
        class_internal = 0
        class_external = 0
        class_p = {'dsa': 0, 'aptitude': 0, 'interview': 0}
        
        if course_ids:
            academic_results = Result.query.filter(Result.course_id.in_(course_ids), Result.examination_type == 'internal').all()
            if academic_results:
                class_internal = sum([r.internal_total for r in academic_results]) / len(academic_results)
                ext = [r.external_marks for r in academic_results if r.external_marks > 0]
                class_external = sum(ext) / len(ext) if ext else 0

            # Placement Score Analysis for class
            student_ids = [s.id for s in all_students]
            if student_ids:
                p_results = Result.query.filter(Result.student_id.in_(student_ids), Result.examination_type == 'placement').all()
                if p_results:
                    class_p['dsa'] = sum([r.dsa_mock_exam for r in p_results]) / len(p_results)
                    class_p['aptitude'] = sum([r.aptitude_score for r in p_results]) / len(p_results)
                    class_p['interview'] = sum([r.interview_score for r in p_results]) / len(p_results)

        # --- SPECIFIC STUDENT ANALYTICS ---
        student_data = None
        if selected_student:
            s_academic = Result.query.filter_by(student_id=selected_student.id, examination_type='internal').all()
            s_p = Result.query.filter_by(student_id=selected_student.id, examination_type='placement').first()
            
            # Academic breakdown with safety checks
            s_internal_count = len(s_academic)
            s_external_list = [r.external_marks for r in s_academic if r.external_marks > 0]
            s_external_count = len(s_external_list)

            student_data = {
                'internal': sum([r.internal_total for r in s_academic]) / s_internal_count if s_internal_count > 0 else 0,
                'external': sum(s_external_list) / s_external_count if s_external_count > 0 else 0,
                'p': {
                    'dsa': s_p.dsa_mock_exam if s_p else 0,
                    'aptitude': s_p.aptitude_score if s_p else 0,
                    'interview': s_p.interview_score if s_p else 0
                }
            }

        return render_template('dashboard/faculty_home.html', 
                             courses=courses, 
                             all_students=all_students,
                             selected_student=selected_student,
                             students_count=students_count,
                             class_internal=round(class_internal, 2),
                             class_external=round(class_external, 2),
                             class_p=class_p,
                             student_data=student_data)
    
    elif current_user.role == 'admin':
        # Admin dashboard
        total_students = Student.query.count()
        total_departments = Department.query.count()
        total_results = Result.query.count()
        
        return render_template('dashboard/admin_home.html', 
                             total_students=total_students,
                             total_departments=total_departments,
                             total_results=total_results)


@dashboard_bp.route('/complete-student-profile', methods=['GET', 'POST'])
@login_required
def complete_student_profile():
    """Complete student profile during registration"""
    user_id = request.args.get('user_id', current_user.id, type=int)
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        registration_number = request.form.get('registration_number')
        department_id = request.form.get('department_id', type=int)
        admission_year = request.form.get('admission_year', type=int)
        
        # Validate required fields
        if not registration_number or not department_id or not admission_year:
            flash('All fields are required.', 'danger')
            return redirect(request.url)
        
        # Check if student profile already exists
        existing = Student.query.filter_by(user_id=user.id).first()
        if existing:
            flash('Student profile already exists.', 'warning')
            return redirect(url_for('dashboard.home'))
        
        # Check if registration number is already taken
        existing_reg = Student.query.filter_by(registration_number=registration_number).first()
        if existing_reg:
            flash('Registration number already exists. Please choose a different one.', 'danger')
            return redirect(request.url)
        
        # Check if department exists
        department = Department.query.get(department_id)
        if not department:
            flash('Invalid department selected.', 'danger')
            return redirect(request.url)
        
        try:
            student = Student(
                user_id=user.id,
                registration_number=registration_number,
                department_id=department_id,
                admission_year=admission_year
            )
            
            db.session.add(student)
            db.session.commit()
            
            flash('Student profile completed successfully!', 'success')
            return redirect(url_for('dashboard.home'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while saving your profile. Please try again.', 'danger')
            print(f"Error creating student profile: {e}")
            return redirect(request.url)
    
    departments = Department.query.all()
    return render_template('dashboard/complete_student_profile.html', departments=departments)


@dashboard_bp.route('/profile')
@login_required
def profile():
    """User profile view"""
    return render_template('dashboard/profile.html', user=current_user)


@dashboard_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    form = UpdateProfileForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Incorrect password', 'danger')
        else:
            current_user.full_name = form.full_name.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Profile updated successfully!', 'success')
    
    return redirect(url_for('dashboard.profile'))


# ============= RESULTS ROUTES =============
@results_bp.route('/view', methods=['GET', 'POST'])
@login_required
def view_results():
    """View results"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    exam_type = request.args.get('exam_type', '', type=str)
    
    query = Result.query
    
    if current_user.role == 'student':
        student = Student.query.filter_by(user_id=current_user.id).first()
        if student:
            query = query.filter_by(student_id=student.id)
    
    if search:
        query = query.join(Student).filter(Student.registration_number.ilike(f'%{search}%'))
    
    if exam_type:
        query = query.filter_by(examination_type=exam_type)
    
    results = query.paginate(page=page, per_page=20)
    
    return render_template('results/view_results.html', results=results, search=search, exam_type=exam_type)


@results_bp.route('/add-marks', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_marks():
    """Unified route to add marks via CSV upload"""
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')
        course_id = request.form.get('course_id', type=int)
        file = request.files.get('file')

        if not file or not course_id:
            flash('Both file and course selection are required.', 'danger')
            return redirect(url_for('results.add_marks'))

        if not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'danger')
            return redirect(url_for('results.add_marks'))

        try:
            import pandas as pd
            df = pd.read_csv(file)
            count = 0
            errors = []

            for _, row in df.iterrows():
                reg_num = str(row['registration_number']).strip()
                student = Student.query.filter_by(registration_number=reg_num).first()
                
                if not student:
                    errors.append(f"Student {reg_num} not found.")
                    continue

                if upload_type == 'internal':
                    result = Result.query.filter_by(
                        student_id=student.id, course_id=course_id, examination_type='internal'
                    ).first()
                    
                    if not result:
                        result = Result(student_id=student.id, course_id=course_id, examination_type='internal', recorded_by=current_user.id)
                    
                    result.cie_assessment_1 = float(row.get('cie1', 0))
                    result.cie_assessment_2 = float(row.get('cie2', 0))
                    result.cie_assessment_3 = float(row.get('cie3', 0))
                    result.mid_term_marks = float(row.get('mid_term', 0))
                    result.assignment_marks = float(row.get('assignment', 0))
                    result.remarks = str(row.get('remarks', ''))
                    result.calculate_internal_total()
                    db.session.add(result)
                
                elif upload_type == 'external':
                    result = Result.query.filter_by(
                        student_id=student.id, course_id=course_id, examination_type='internal'
                    ).first()
                    
                    if not result:
                        errors.append(f"Internal marks missing for student {reg_num}. External marks skipped.")
                        continue
                    
                    result.external_marks = float(row.get('external_marks', 0))
                    result.remarks = str(row.get('remarks', ''))
                    result.calculate_academic_total()
                    result.assign_grade()
                    db.session.add(result)
                
                elif upload_type == 'placement':
                    # Placement scores are not specific to a course_id
                    result = Result.query.filter_by(
                        student_id=student.id, examination_type='placement', course_id=None
                    ).first()
                    
                    if not result:
                        result = Result(student_id=student.id, examination_type='placement', recorded_by=current_user.id)
                    
                    result.dsa_mock_exam = float(row.get('dsa', 0))
                    result.oops_mock_exam = float(row.get('oops', 0))
                    result.dbms_mock_exam = float(row.get('dbms', 0))
                    result.programming_mock_exam = float(row.get('programming', 0))
                    result.aptitude_score = float(row.get('aptitude', 0))
                    result.interview_score = float(row.get('interview', 0))
                    result.remarks = str(row.get('remarks', ''))
                    result.calculate_placement_average()
                    db.session.add(result)
                
                count += 1

            db.session.commit()
            
            if errors:
                flash(f'Processed {count} records. Following errors occurred: ' + ", ".join(errors[:3]), 'warning')
            else:
                flash(f'Successfully processed {count} student marks!', 'success')
            
            return redirect(url_for('results.view_results'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing CSV: {str(e)}', 'danger')
            return redirect(url_for('results.add_marks'))

    # GET request: Show the upload page
    user_role = str(current_user.role).lower()
    
    if user_role == 'admin':
        # Admins can see all courses
        courses = Course.query.all()
    else:
        # Faculty see only their assigned courses
        courses = Course.query.filter_by(faculty_id=current_user.id).all()
    
    return render_template('results/add_marks.html', courses=courses)


@results_bp.route('/add-internal', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_internal_marks():
    """Add internal exam marks"""
    form = InternalExamForm()
    # Populate choices from database
    if current_user.role == 'admin':
        courses = Course.query.all()
    else:
        courses = Course.query.filter_by(faculty_id=current_user.id).all()
        
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}") for c in courses]
    
    if form.validate_on_submit():
        student = Student.query.filter_by(
            registration_number=form.student_id.data
        ).first()
        
        if not student:
            flash('Student not found. Please check the registration number.', 'danger')
            return redirect(url_for('results.add_internal_marks'))
        
        course = Course.query.get(form.course_id.data)
        if not course:
            flash('Course not found', 'danger')
            return redirect(url_for('results.add_internal_marks'))
        
        # Check if result already exists
        result = Result.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            examination_type='internal'
        ).first()
        
        if result:
            # Update existing
            result.cie_assessment_1 = form.cie_assessment_1.data
            result.cie_assessment_2 = form.cie_assessment_2.data
            result.cie_assessment_3 = form.cie_assessment_3.data
            result.mid_term_marks = form.mid_term_marks.data
            result.assignment_marks = form.assignment_marks.data
            result.remarks = form.remarks.data
            action = 'UPDATE'
        else:
            # Create new
            result = Result(
                student_id=student.id,
                course_id=course.id,
                examination_type='internal',
                cie_assessment_1=form.cie_assessment_1.data,
                cie_assessment_2=form.cie_assessment_2.data,
                cie_assessment_3=form.cie_assessment_3.data,
                mid_term_marks=form.mid_term_marks.data,
                assignment_marks=form.assignment_marks.data,
                remarks=form.remarks.data,
                recorded_by=current_user.id
            )
            action = 'CREATE'
        
        result.calculate_internal_total()
        db.session.add(result)
        db.session.commit()
        
        log_audit_action(current_user.id, action, 'results', result.id, 
                        new_values={'internal_total': result.internal_total})
        
        flash('Internal marks saved successfully!', 'success')
        return redirect(url_for('results.view_results'))
    
    return render_template('results/add_internal_marks.html', form=form)


@results_bp.route('/add-external', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_external_marks():
    """Add external exam marks"""
    form = ExternalExamForm()
    # Populate choices from database
    if current_user.role == 'admin':
        courses = Course.query.all()
    else:
        courses = Course.query.filter_by(faculty_id=current_user.id).all()
        
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_name}") for c in courses]
    
    if form.validate_on_submit():
        student = Student.query.filter_by(
            registration_number=form.student_id.data
        ).first()
        
        if not student:
            flash('Student not found. Please check the registration number.', 'danger')
            return redirect(url_for('results.add_external_marks'))
        
        course = Course.query.get(form.course_id.data)
        if not course:
            flash('Course not found', 'danger')
            return redirect(url_for('results.add_external_marks'))
        
        # Get internal result
        internal_result = Result.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            examination_type='internal'
        ).first()
        
        if internal_result:
            internal_result.external_marks = form.external_marks.data
            internal_result.calculate_academic_total()
            internal_result.assign_grade()
            internal_result.remarks = form.remarks.data
            db.session.add(internal_result)
        else:
            flash('Internal marks must be recorded first', 'warning')
            return redirect(url_for('results.add_external_marks'))
        
        db.session.commit()
        log_audit_action(current_user.id, 'UPDATE', 'results', internal_result.id,
                        new_values={'external_marks': form.external_marks.data, 
                                   'academic_total': internal_result.academic_total})
        
        flash('External marks saved successfully!', 'success')
        return redirect(url_for('results.view_results'))
    
    return render_template('results/add_external_marks.html', form=form)


@results_bp.route('/add-placement', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_placement_scores():
    """Add placement preparation scores"""
    form = PlacementPrepForm()
    
    if form.validate_on_submit():
        student = Student.query.filter_by(
            registration_number=form.student_id.data
        ).first()
        
        if not student:
            flash('Student not found. Please check the registration number.', 'danger')
            return redirect(url_for('results.add_placement_scores'))
        
        # Create or update placement result
        result = Result.query.filter_by(
            student_id=student.id,
            examination_type='placement',
            course_id=None
        ).first()
        
        if result:
            result.dsa_mock_exam = form.dsa_mock_exam.data
            result.oops_mock_exam = form.oops_mock_exam.data
            result.dbms_mock_exam = form.dbms_mock_exam.data
            result.programming_mock_exam = form.programming_mock_exam.data
            result.aptitude_score = form.aptitude_score.data
            result.interview_score = form.interview_score.data
        else:
            result = Result(
                student_id=student.id,
                examination_type='placement',
                dsa_mock_exam=form.dsa_mock_exam.data,
                oops_mock_exam=form.oops_mock_exam.data,
                dbms_mock_exam=form.dbms_mock_exam.data,
                programming_mock_exam=form.programming_mock_exam.data,
                aptitude_score=form.aptitude_score.data,
                interview_score=form.interview_score.data,
                remarks=form.remarks.data,
                recorded_by=current_user.id
            )
        
        result.calculate_placement_average()
        db.session.add(result)
        db.session.commit()
        
        flash('Placement scores saved successfully!', 'success')
        return redirect(url_for('results.view_results'))
    
    return render_template('results/add_placement_scores.html', form=form)


@results_bp.route('/export-csv')
@login_required
@faculty_required
def export_csv():
    """Export results to CSV"""
    csv_file = export_results_to_csv()
    return send_file(csv_file, mimetype='text/csv', 
                    as_attachment=True, download_name='exam_results.csv')


@results_bp.route('/export-pdf')
@login_required
@faculty_required
def export_pdf():
    """Export results to PDF"""
    pdf_file = export_results_to_pdf()
    return send_file(pdf_file, mimetype='application/pdf',
                    as_attachment=True, download_name='exam_results.pdf')


# ============= ANALYTICS ROUTES =============
@analytics_bp.route('/student/<int:student_id>')
@login_required
def student_analytics(student_id):
    """Student analytics and statistics"""
    student = Student.query.get_or_404(student_id)
    
    # Check authorization
    if current_user.role == 'student':
        if current_user.id != student.user_id:
            flash('You do not have permission to view this student\'s analytics.', 'danger')
            return redirect(url_for('dashboard.home'))
    
    stats = get_student_statistics(student_id)
    results = Result.query.filter_by(student_id=student_id).all()
    gpa = calculate_student_gpa(student_id)
    
    return render_template('analytics/student_analytics.html', 
                         student=student, stats=stats, results=results, gpa=gpa)


@analytics_bp.route('/department/<int:department_id>')
@login_required
@admin_required
def department_analytics(department_id):
    """Department analytics"""
    department = Department.query.get_or_404(department_id)
    stats = get_department_statistics(department_id)
    
    return render_template('analytics/department_analytics.html', 
                         department=department, stats=stats)


@analytics_bp.route('/course/<int:course_id>')
@login_required
@faculty_required
def course_analytics(course_id):
    """Course analytics"""
    course = Course.query.get_or_404(course_id)
    analytics = get_course_analytics(course_id)
    
    return render_template('analytics/course_analytics.html', 
                         course=course, analytics=analytics)


# ============= ADMIN ROUTES =============
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    total_students = Student.query.count()
    total_departments = Department.query.count()
    total_courses = Course.query.count()
    total_users = User.query.count()
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_departments=total_departments,
                         total_courses=total_courses,
                         total_users=total_users,
                         recent_logs=recent_logs)


@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage users"""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    
    # Build query with search filter
    query = User.query
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            (User.username.ilike(search)) | 
            (User.full_name.ilike(search)) | 
            (User.email.ilike(search))
        )
    
    users = query.paginate(page=page, per_page=20)
    
    return render_template('admin/manage_users.html', users=users, search_query=search_query)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    log_audit_action(current_user.id, 'TOGGLE_ACTIVE', 'users', user_id,
                    new_values={'is_active': user.is_active})
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {status} successfully!', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/departments')
@login_required
@admin_required
def manage_departments():
    """Manage departments"""
    page = request.args.get('page', 1, type=int)
    departments = Department.query.paginate(page=page, per_page=20)
    
    return render_template('admin/manage_departments.html', departments=departments)


@admin_bp.route('/departments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_department():
    """Create new department"""
    form = CreateDepartmentForm()
    
    if form.validate_on_submit():
        dept = Department(name=form.name.data, code=form.code.data)
        db.session.add(dept)
        db.session.commit()
        
        log_audit_action(current_user.id, 'CREATE', 'departments', dept.id)
        flash('Department created successfully!', 'success')
        return redirect(url_for('admin.manage_departments'))
    
    return render_template('admin/create_department.html', form=form)


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def view_audit_logs():
    """View audit logs"""
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
    
    return render_template('admin/audit_logs.html', logs=logs)
