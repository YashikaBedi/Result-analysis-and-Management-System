from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import json
from app import db
from app.models import Result, Student, Course, User, AuditLog
from flask import request

# Optional imports for analytics - will be available when pandas is installed
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

def calculate_student_gpa(student_id):
    """Calculate cumulative GPA for a student"""
    results = Result.query.filter_by(student_id=student_id, examination_type='internal').all()
    
    if not results:
        return 0.0
    
    total_grade_points = 0
    total_credits = 0
    
    for result in results:
        if result.course:
            total_grade_points += result.grade_point * result.course.credits
            total_credits += result.course.credits
    
    if total_credits == 0:
        return 0.0
    
    return round(total_grade_points / total_credits, 2)


def get_student_statistics(student_id):
    """Get comprehensive statistics for a student"""
    results = Result.query.filter_by(student_id=student_id).all()
    
    if not results:
        return None
    
    academic_results = [r for r in results if r.examination_type == 'internal']
    placement_results = [r for r in results if r.examination_type == 'placement']
    
    stats = {
        'total_courses': len(academic_results),
        'passed_courses': len([r for r in academic_results if r.pass_fail == 'Pass']),
        'failed_courses': len([r for r in academic_results if r.pass_fail == 'Fail']),
        'average_marks': round(sum([r.academic_total for r in academic_results]) / len(academic_results), 2) if academic_results else 0,
        'gpa': calculate_student_gpa(student_id),
        'placement_average': round(sum([r.placement_average for r in placement_results]) / len(placement_results), 2) if placement_results else 0,
    }
    
    return stats


def get_department_statistics(department_id):
    """Get statistics for a department"""
    from app.models import Department, Program, Enrollment
    
    department = Department.query.get(department_id)
    if not department:
        return None
    
    # Get all students in department
    students = Student.query.filter_by(department_id=department_id).all()
    
    stats = {
        'total_students': len(students),
        'total_courses': 0,
        'average_pass_rate': 0,
        'class_average': 0,
    }
    
    if students:
        all_results = []
        for student in students:
            results = Result.query.filter_by(student_id=student.id, examination_type='internal').all()
            all_results.extend(results)
        
        if all_results:
            stats['total_courses'] = len(set([r.course_id for r in all_results]))
            pass_count = len([r for r in all_results if r.pass_fail == 'Pass'])
            stats['average_pass_rate'] = round((pass_count / len(all_results)) * 100, 2)
            stats['class_average'] = round(sum([r.academic_total for r in all_results]) / len(all_results), 2)
    
    return stats


def export_results_to_csv(filters=None):
    """Export results to CSV format"""
    if not HAS_PANDAS:
        raise RuntimeError("Pandas is required for CSV export. Install with: pip install pandas")
    
    query = Result.query
    
    if filters:
        if 'student_id' in filters:
            query = query.filter_by(student_id=filters['student_id'])
        if 'course_id' in filters:
            query = query.filter_by(course_id=filters['course_id'])
        if 'examination_type' in filters:
            query = query.filter_by(examination_type=filters['examination_type'])
    
    results = query.all()
    
    data = []
    for result in results:
        row = {
            'Student ID': result.student.registration_number if result.student else '',
            'Student Name': result.student.user.full_name if result.student else '',
            'Course Code': result.course.course_code if result.course else '',
            'Course Name': result.course.course_name if result.course else '',
            'Exam Type': result.examination_type,
            'Internal Total': result.internal_total,
            'External Marks': result.external_marks,
            'Academic Total': result.academic_total,
            'Grade': result.grade,
            'Pass/Fail': result.pass_fail,
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return output


def export_results_to_pdf(student_id=None, course_id=None):
    """Export results to PDF format"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
    except ImportError:
        raise RuntimeError("ReportLab is required for PDF export. Install with: pip install reportlab")
    
    query = Result.query
    
    if student_id:
        query = query.filter_by(student_id=student_id)
    if course_id:
        query = query.filter_by(course_id=course_id)
    
    results = query.all()
    
    # Create PDF
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=1
    )
    
    elements.append(Paragraph('College Exam Results Report', title_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Create table
    table_data = [['Student ID', 'Course', 'Internal', 'External', 'Total', 'Grade', 'Status']]
    
    for result in results:
        student_id_val = result.student.registration_number if result.student else 'N/A'
        course_name = result.course.course_code if result.course else 'N/A'
        
        table_data.append([
            student_id_val,
            course_name,
            str(round(result.internal_total, 2)),
            str(round(result.external_marks, 2)),
            str(round(result.academic_total, 2)),
            result.grade,
            result.pass_fail
        ])
    
    # Style table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    
    return pdf_buffer


def log_audit_action(user_id, action, table_name, record_id=None, old_values=None, new_values=None):
    """Log user actions for audit trail"""
    ip_address = request.remote_addr if request else None
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address
    )
    
    db.session.add(audit_log)
    db.session.commit()


def search_results(query_string, filters=None):
    """Search results based on query and filters"""
    results = db.session.query(Result).join(Student).join(Course)
    
    # Search by student name or ID
    if query_string:
        results = results.filter(
            db.or_(
                Student.registration_number.ilike(f'%{query_string}%'),
                User.full_name.ilike(f'%{query_string}%')
            )
        )
    
    # Apply additional filters
    if filters:
        if 'course_id' in filters and filters['course_id']:
            results = results.filter_by(course_id=filters['course_id'])
        if 'examination_type' in filters and filters['examination_type']:
            results = results.filter_by(examination_type=filters['examination_type'])
    
    return results.all()


def get_course_analytics(course_id):
    """Get analytics for a specific course"""
    results = Result.query.filter_by(course_id=course_id, examination_type='internal').all()
    
    if not results:
        return None
    
    marks = [r.academic_total for r in results]
    
    analytics = {
        'total_students': len(results),
        'average': round(sum(marks) / len(marks), 2),
        'median': round(sorted(marks)[len(marks) // 2], 2),
        'min': min(marks),
        'max': max(marks),
        'pass_count': len([r for r in results if r.pass_fail == 'Pass']),
        'pass_rate': round((len([r for r in results if r.pass_fail == 'Pass']) / len(results)) * 100, 2),
        'grade_distribution': get_grade_distribution(results),
    }
    
    return analytics


def get_grade_distribution(results):
    """Get grade distribution from results"""
    grades = {}
    for result in results:
        if result.grade:
            grades[result.grade] = grades.get(result.grade, 0) + 1
    
    return grades
