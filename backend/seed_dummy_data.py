import sys
import os
from datetime import datetime

# Add the current directory to path so we can import app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, Student, Department, Program, Course, Result, Enrollment, UserRole, AuditLog

def seed_data():
    app = create_app('development')
    
    with app.app_context():
        print("Starting data seeding...")
        
        # 1. Clear existing data (Order matters due to foreign keys)
        print("Cleaning old data...")
        AuditLog.query.delete()
        Result.query.delete()
        Enrollment.query.delete()
        # Clear faculty_department relationship entries
        db.session.execute(db.delete(db.metadata.tables['faculty_department']))
        
        Course.query.delete()
        Program.query.delete()
        Student.query.delete()
        Department.query.delete()
        User.query.delete()
        db.session.commit()

        # 2. Create Users (Admin, Faculty, Students)
        print("Creating users...")
        
        admin = User(username='admin', email='admin@college.edu', full_name='System Administrator', role='admin')
        admin.set_password('admin123')
        
        f1 = User(username='profsarma', email='sarma@college.edu', full_name='Prof. Rajesh Sarma', role='faculty')
        f1.set_password('faculty123')
        
        f2 = User(username='drkapoor', email='kapoor@college.edu', full_name='Dr. Anita Kapoor', role='faculty')
        f2.set_password('faculty123')
        
        db.session.add_all([admin, f1, f2])
        db.session.commit()

        # 3. Create Departments
        print("Creating departments...")
        depts = [
            Department(name='Master of Computer Application', code='MCA'),
            Department(name='Bachelor of Computer Application', code='BCA'),
            Department(name='Master of Business Administration', code='MBA')
        ]
        db.session.add_all(depts)
        db.session.commit()

        # 4. Create Programs (Semesters)
        print("Creating programs...")
        p1 = Program(department_id=depts[0].id, semester=1, academic_year='2023-2024')
        p2 = Program(department_id=depts[0].id, semester=2, academic_year='2023-2024')
        p3 = Program(department_id=depts[1].id, semester=1, academic_year='2023-2024')
        db.session.add_all([p1, p2, p3])
        db.session.commit()

        # 5. Create Courses
        print("Creating courses...")
        c1 = Course(program_id=p1.id, course_code='MCA101', course_name='Database Management Systems', credits=4, faculty_id=f1.id)
        c2 = Course(program_id=p1.id, course_code='MCA102', course_name='Data Structures & Algorithms', credits=4, faculty_id=f1.id)
        c3 = Course(program_id=p2.id, course_code='MCA201', course_name='Web Technologies', credits=3, faculty_id=f2.id)
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        # 6. Create Students and Profiles
        print("Creating students...")
        student_names = [
            ('rahul01', 'Rahul Kumar', 'MCA/2023/001'),
            ('priya02', 'Priya Singh', 'MCA/2023/002'),
            ('amit03', 'Amit Sharma', 'MCA/2023/003'),
            ('sneha04', 'Sneha Patel', 'BCA/2023/001')
        ]
        
        students = []
        for uname, fname, reg in student_names:
            u = User(username=uname, email=f'{uname}@student.edu', full_name=fname, role='student')
            u.set_password('student123')
            db.session.add(u)
            db.session.commit() # Commit to get user ID
            
            s = Student(user_id=u.id, registration_number=reg, department_id=depts[0].id if 'MCA' in reg else depts[1].id, admission_year=2023)
            db.session.add(s)
            students.append(s)
        
        db.session.commit()

        # 7. Enrollments
        print("Creating enrollments...")
        for s in students:
            if s.department_id == depts[0].id:
                db.session.add(Enrollment(student_id=s.id, course_id=c1.id))
                db.session.add(Enrollment(student_id=s.id, course_id=c2.id))
            else:
                db.session.add(Enrollment(student_id=s.id, course_id=c3.id))
        db.session.commit()

        # 8. Create Results
        print("Creating sample results...")
        import random
        for s in students:
            if s.department_id == depts[0].id:
                # Result for c1
                r = Result(student_id=s.id, course_id=c1.id, examination_type='internal',
                           cie_assessment_1=random.uniform(7, 10),
                           cie_assessment_2=random.uniform(7, 10),
                           cie_assessment_3=random.uniform(7, 10),
                           mid_term_marks=random.uniform(15, 20),
                           assignment_marks=random.uniform(8, 10))
                r.calculate_internal_total()
                r.external_marks = random.uniform(40, 60)
                r.calculate_academic_total()
                r.assign_grade()
                db.session.add(r)
        
        db.session.commit()
        print("\n" + "="*30)
        print("✓ DUMMY DATA SEEDED SUCCESSFULLY!")
        print("="*30)

if __name__ == '__main__':
    seed_data()
