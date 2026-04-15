import sys
import os
import random
from datetime import datetime

# Add the current directory to path so we can import app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Student, Course, Result, Enrollment

def seed_results_bulk():
    app = create_app('development')
    
    with app.app_context():
        print("Starting Bulk Results Seeding...")
        
        students = Student.query.all()
        courses = Course.query.all()
        
        if not students or not courses:
            print("No students or courses found. Please run seed_dummy_data.py first.")
            return

        placeholder_course_id = courses[0].id
        seeded_count = 0
        
        # Ensure plenty of academic entries
        for s in students:
            # Get courses this student is enrolled in
            enrolled_courses = [e.course_id for e in s.enrollments]
            for c_id in enrolled_courses:
                # Check if result already exists
                existing = Result.query.filter_by(
                    student_id=s.id, 
                    course_id=c_id, 
                    examination_type='internal'
                ).first()
                
                if not existing:
                    res = Result(
                        student_id=s.id,
                        course_id=c_id,
                        examination_type='internal',
                        cie_assessment_1=random.uniform(7, 10),
                        cie_assessment_2=random.uniform(7, 10),
                        cie_assessment_3=random.uniform(7, 10),
                        mid_term_marks=random.uniform(14, 20),
                        assignment_marks=random.uniform(8, 10),
                        external_marks=random.uniform(40, 60)
                    )
                    res.calculate_internal_total()
                    res.calculate_academic_total()
                    res.assign_grade()
                    db.session.add(res)
                    seeded_count += 1

        # Placement Results for everyone
        for s in students:
            existing_p = Result.query.filter_by(student_id=s.id, examination_type='placement').first()
            if not existing_p:
                p_res = Result(
                    student_id=s.id,
                    course_id=placeholder_course_id,
                    examination_type='placement',
                    dsa_mock_exam=random.uniform(70, 95),
                    oops_mock_exam=random.uniform(70, 95),
                    dbms_mock_exam=random.uniform(70, 95),
                    programming_mock_exam=random.uniform(70, 95),
                    aptitude_score=random.uniform(70, 95),
                    interview_score=random.uniform(70, 95)
                )
                p_res.calculate_placement_average()
                db.session.add(p_res)
                seeded_count += 1
                
        db.session.commit()
        print(f"Successfully added {seeded_count} new records!")
        print(f"Total Results in database: {Result.query.count()}")

if __name__ == '__main__':
    seed_results_bulk()
