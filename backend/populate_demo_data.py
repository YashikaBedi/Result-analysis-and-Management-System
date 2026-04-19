#!/usr/bin/env python
"""
Comprehensive Demo Data Population Script
Populates the database with realistic college exam data for testing and demonstration.
"""

import random
from datetime import datetime, timedelta
from app import create_app, db
from app.models import (
    User, UserRole, Department, Program, Course, Student,
    Enrollment, Result, AcademicCalendar
)

def create_departments():
    """Create 2 main departments."""
    print("Creating departments...")
    dept1 = Department(name="MCA", code="MCA")
    dept2 = Department(name="B.Tech", code="BTECH")

    db.session.add_all([dept1, dept2])
    db.session.commit()
    return [dept1, dept2]

def create_programs(departments):
    """Create programs for each department."""
    print("Creating programs...")
    programs = []
    for dept in departments:
        for year in range(1, 4):  # 3 years
            program = Program(
                department_id=dept.id,
                semester=year,
                academic_year=f"{2024 + year - 1}-{2024 + year}"
            )
            programs.append(program)
    db.session.add_all(programs)
    db.session.commit()
    return programs

def create_mca_sem1_data(dept):
    """Create MCA Semester 1 data (Sections A & B) based on required subjects."""
    print("Creating MCA Semester 1 Data...")
    
    # 1. Program
    program = Program(department_id=dept.id, semester=1, academic_year="2024-2025")
    db.session.add(program)
    db.session.commit()
    
    # 2. Faculty
    faculty_list = [
        ("Dr. Deepshikha", "deepshikha@college.edu", "deepshikha"),
        ("Dr. Deepti S", "deepti_s@college.edu", "deepti_s"),
        ("Mr. JPS", "jps@college.edu", "jps"),
        ("Dr. Deepti K", "deepti_k@college.edu", "deepti_k"),
        ("Dr. Manjot", "manjot@college.edu", "manjot"),
        ("Dr. Archana", "archana@college.edu", "archana"),
        ("Mr. Harsh", "harsh@college.edu", "harsh")
    ]
    faculty_map = {}
    for name, email, username in faculty_list:
        user = User(username=username, email=email, full_name=name, role='faculty')
        user.set_password('faculty123')
        db.session.add(user)
        faculty_map[username] = user
    db.session.commit()
    
    # 3. Courses (Section A & B)
    # Mapping based on timetable
    subjects = [
        ("Computer Networks", "MCA101", "deepshikha", "deepshikha"), # Same for both sections
        ("Operating Systems", "MCA102", "deepti_s", "deepti_s"),
        ("Data Structures", "MCA103", "jps", "jps"),
        ("Database Management", "MCA104", "deepti_k", "manjot"), # Sec A: Deepti K, Sec B: Manjot
        ("OOPS & Java", "MCA105", "archana", "archana"),
        ("Aptitude", "MCA106", "harsh", "harsh")
    ]
    
    courses = []
    for name, code, fac_a, fac_b in subjects:
        # Section A
        c_a = Course(
            program_id=program.id, course_code=code, course_name=name, credits=4,
            section='A', faculty_id=faculty_map[fac_a].id
        )
        # Section B
        c_b = Course(
            program_id=program.id, course_code=code, course_name=name, credits=4,
            section='B', faculty_id=faculty_map[fac_b].id
        )
        courses.extend([c_a, c_b])
    db.session.add_all(courses)
    db.session.commit()
    
    # 4. Students
    first_names = ["Amit", "Priya", "Rahul", "Sneha", "Vikram", "Anjali", "Rohit", "Kavita", "Suresh", "Meera", "Arjun", "Pooja", "Karan", "Neha", "Vivek", "Swati"]
    last_names = ["Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Jain", "Agarwal", "Chauhan", "Yadav", "Mishra", "Tiwari"]
    
    students = []
    student_counter = 1
    for section in ['A', 'B']:
        for _ in range(30):  # 30 students per section
            username = f"mca{student_counter:03d}"
            user = User(
                username=username,
                email=f"{username}@college.edu",
                full_name=f"{random.choice(first_names)} {random.choice(last_names)}",
                role='student'
            )
            user.set_password('student123')
            db.session.add(user)
            db.session.commit()
            
            student = Student(
                user_id=user.id,
                registration_number=f"MCA24{section}{student_counter:03d}",
                department_id=dept.id,
                admission_year=2024,
                section=section
            )
            db.session.add(student)
            db.session.commit()
            students.append((user, student))
            student_counter += 1
            
    # 5. Enrollments & Results
    for user, student in students:
        sec_courses = [c for c in courses if c.section == student.section]
        for course in sec_courses:
            # Enroll
            enrollment = Enrollment(student_id=student.id, course_id=course.id, enrolled_date=datetime.now())
            db.session.add(enrollment)
            
            # Internal Marks (Max 40)
            c1 = random.randint(4, 10)
            c2 = random.randint(4, 10)
            c3 = random.randint(4, 10)
            ie1 = random.randint(8, 20)
            ie2 = random.randint(8, 20)
            asn = random.randint(5, 10)
            pf = random.randint(5, 10)
            ip = random.randint(10, 20)
            
            # New 10 (CIE) + 20 (IE) + 10 (Other) logic
            cie_avg = (c1 + c2 + c3) / 3
            ie_avg = (ie1 + ie2) / 2
            other = min(10, asn + pf + ip)
            internal_total = round(cie_avg + ie_avg + other, 1)
            internal_total = min(40.0, internal_total)
            
            external = random.randint(20, 60)
            total = internal_total + external
            
            # Grade
            grade = 'F' if total < 40 else ('A+' if total >= 90 else ('A' if total >= 80 else ('B+' if total >= 70 else ('B' if total >= 60 else 'C'))))
            
            result = Result(
                student_id=student.id,
                course_id=course.id,
                examination_type='internal',
                cie_1=c1, cie_2=c2, cie_3=c3,
                internal_exam_1=ie1, internal_exam_2=ie2,
                assignment_marks=asn, practical_file_marks=pf, internal_practical_marks=ip,
                internal_total=internal_total,
                external_marks=external,
                academic_total=total,
                pass_fail='Pass' if total >= 40 else 'Fail',
                grade=grade
            )
            db.session.add(result)
            
        # Placement Data
        p_result = Result(
            student_id=student.id,
            examination_type='placement',
            dsa_mock_exam=random.randint(40, 95),
            oops_mock_exam=random.randint(45, 98),
            dbms_mock_exam=random.randint(50, 92),
            programming_mock_exam=random.randint(35, 90),
            aptitude_score=random.randint(55, 100),
            interview_score=random.randint(60, 95)
        )
        p_result.calculate_placement_average()
        db.session.add(p_result)

    # 6. Historical Data for Trends (Top 10 students get a previous semester)
    prev_program = Program(department_id=dept.id, semester=2, academic_year="2023-2024")
    db.session.add(prev_program)
    db.session.commit()
    
    prev_course = Course(
        program_id=prev_program.id,
        course_code="MCA099",
        course_name="Introduction to IT",
        credits=3,
        section='A',
        faculty_id=faculty_map["deepshikha"].id
    )
    db.session.add(prev_course)
    db.session.commit()

    for i in range(10):
        _, student = students[i]
        enrollment = Enrollment(student_id=student.id, course_id=prev_course.id, enrolled_date=datetime.now() - timedelta(days=200))
        db.session.add(enrollment)
        
        # Historical marks (slightly lower to show improvement)
        total = random.randint(45, 65)
        result = Result(
            student_id=student.id,
            course_id=prev_course.id,
            examination_type='internal',
            internal_total=total * 0.4,
            external_marks=total * 0.6,
            academic_total=total,
            pass_fail='Pass',
            grade='C',
            recorded_by=faculty_map["deepshikha"].id
        )
        db.session.add(result)

    db.session.commit()
    print("DONE: MCA Semester 1 Data completely seeded (with historical trends).")
    return students, courses



def create_academic_calendar():
    """Create sample academic calendar events."""
    print("Creating academic calendar...")
    events = [
        ("Semester 1 Start", "2024-08-01", "2024-08-01"),
        ("Mid-term Exams", "2024-10-15", "2024-10-25"),
        ("Semester 1 End", "2024-11-30", "2024-11-30"),
        ("Winter Break", "2024-12-01", "2024-12-31"),
        ("Semester 2 Start", "2025-01-01", "2025-01-01"),
        ("Final Exams", "2025-04-15", "2025-05-15"),
        ("Results Declaration", "2025-06-01", "2025-06-01"),
    ]

    calendar_events = []
    for title, start_date, end_date in events:
        event = AcademicCalendar(
            title=title,
            description=f"{title} for all departments",
            start_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
            end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
            event_type="academic"
        )
        calendar_events.append(event)

    db.session.add_all(calendar_events)
    db.session.commit()
    return calendar_events

def main():
    """Main function to populate all demo data."""
    print("Starting comprehensive demo data population...")

    app = create_app()
    with app.app_context():
        # Clear existing data
        print("Clearing existing data...")
        db.session.query(Result).delete()
        db.session.query(Enrollment).delete()
        db.session.query(Student).delete()
        db.session.query(Course).delete()
        db.session.query(Program).delete()
        db.session.query(Department).delete()
        db.session.query(User).delete()
        db.session.query(AcademicCalendar).delete()
        db.session.commit()

        # Create admin
        admin = User(
            username='admin',
            email='admin@college.edu',
            full_name='System Administrator',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

        # Create data hierarchy
        departments = create_departments()
        mca_dept = departments[0]
        
        # Call MCA Sem 1 specific population script
        students, courses = create_mca_sem1_data(mca_dept)
        
        calendar = create_academic_calendar()

        print("DONE: Demo data population completed!")
        print(f"   Departments: {len(departments)}")
        print(f"   MCA Courses: {len(courses)}")
        print(f"   MCA Students: {len(students)}") 
        print(f"   Calendar Events: {len(calendar)}")
        print("\nLogin Credentials:")
        print("   Admin: admin / admin123")
        print("   Faculty: deepshikha / faculty123 (or deepti_k, manjot, archana)")
        print("   Students: mca001 / student123 (up to mca060)")

if __name__ == "__main__":
    main()
