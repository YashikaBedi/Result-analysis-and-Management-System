import os
from app import create_app, db
from app.models import (
    User, UserRole, Department, Program, Course,
    Student, Enrollment, Result, LoginHistory, AcademicCalendar
)

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

app = create_app()
with app.app_context():
    print("Testing dashboard logic...")
    try:
        total_users = User.query.count()
        total_students = Student.query.count()
        total_departments = Department.query.count()
        total_courses = Course.query.count()
        total_results = Result.query.count()
        pending_resets = User.query.filter_by(password_reset_requested=True).all()
        recent_logins = LoginHistory.query.order_by(LoginHistory.timestamp.desc()).limit(15).all()
        
        print(f"Stats: users={total_users}, students={total_students}, depts={total_departments}")
        
        dept_stats = get_department_ranking()
        print("Dept Stats computed successfully.")
        
        import json
        print(json.dumps(dept_stats, indent=2))
        
        # Test template context variable failure points
        for log in recent_logins:
             print(f"Log user: {log.user.full_name if log.user else 'NONE'}")

    except Exception as e:
        import traceback
        traceback.print_exc()
