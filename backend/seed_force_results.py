import sys
import os
import random
from datetime import datetime

# Add the current directory to path so we can import app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, Student, Department, Course, Result, Enrollment

def seed_force_20_plus():
    app = create_app('development')
    
    with app.app_context():
        print("Starting Force Seeding (Target: 20+ Records)...")
        
        # 1. Ensure we have enough students
        mca_dept = Department.query.filter_by(code='MCA').first()
        courses = Course.query.all()
        
        current_students_count = Student.query.count()
        needed_students = 10 if current_students_count < 15 else 5
        
        print(f"Creating {needed_students} extra students...")
        for i in range(needed_students):
            uname = f"test_user_{random.randint(1000, 9999)}"
            u = User(username=uname, email=f"{uname}@test.edu", full_name=f"Test Student {i+1}", role='student')
            u.set_password('student123')
            db.session.add(u)
            db.session.commit()
            
            s = Student(user_id=u.id, registration_number=f"MCA/2023/EX-{i+100}", department_id=mca_dept.id, admission_year=2023)
            db.session.add(s)
            db.session.commit()
            
            # Enroll in all MCA courses
            for c in courses:
                if 'MCA' in c.course_code:
                    db.session.add(Enrollment(student_id=s.id, course_id=c.id))
        
        db.session.commit()
        
        # 2. Add results for new and existing students
        all_students = Student.query.all()
        placeholder_course_id = courses[0].id
        seeded_new = 0
        
        for s in all_students:
            enrolled_courses = [e.course_id for e in s.enrollments]
            for c_id in enrolled_courses:
                existing = Result.query.filter_by(student_id=s.id, course_id=c_id, examination_type='internal').first()
                if not existing:
                    res = Result(
                        student_id=s.id,
                        course_id=c_id,
                        examination_type='internal',
                        cie_assessment_1=random.uniform(5, 10),
                        cie_assessment_2=random.uniform(5, 10),
                        cie_assessment_3=random.uniform(5, 10),
                        mid_term_marks=random.uniform(10, 20),
                        assignment_marks=random.uniform(5, 10),
                        external_marks=random.uniform(25, 60)
                    )
                    res.calculate_internal_total()
                    res.calculate_academic_total()
                    res.assign_grade()
                    db.session.add(res)
                    seeded_new += 1
            
            # Placement results
            existing_p = Result.query.filter_by(student_id=s.id, examination_type='placement').first()
            if not existing_p:
                p_res = Result(
                    student_id=s.id,
                    course_id=placeholder_course_id,
                    examination_type='placement',
                    dsa_mock_exam=random.uniform(50, 98),
                    oops_mock_exam=random.uniform(55, 95),
                    dbms_mock_exam=random.uniform(60, 95),
                    programming_mock_exam=random.uniform(50, 98),
                    aptitude_score=random.uniform(50, 95),
                    interview_score=random.uniform(50, 95)
                )
                p_res.calculate_placement_average()
                db.session.add(p_res)
                seeded_new += 1
        
        db.session.commit()
        print(f"Success! Added {seeded_new} new records.")
        print(f"Final Count in Result table: {Result.query.count()}")

if __name__ == '__main__':
    seed_force_20_plus()
