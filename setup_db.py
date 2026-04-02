#!/usr/bin/env python
"""
Database initialization and admin user creation script
"""

from app import create_app, db
from app.models import User, Department, Program, Course, Student
import os

def init_database():
    """Initialize the database"""
    app = create_app('development')
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        
        # Create admin user
        print("\nCreating admin user...")
        
        # Check if admin already exists
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("✓ Admin user already exists!")
        else:
            admin = User(
                username='admin',
                email='admin@college.edu',
                full_name='System Administrator',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(f"✓ Admin user created!")
            print(f"   Username: admin")
            print(f"   Password: admin123")
        
        # Create sample departments
        print("\nCreating sample departments...")
        departments_data = [
            ('Master of Computer Application', 'MCA'),
            ('Bachelor of Business Administration', 'BBA'),
            ('Bachelor of Computer Application', 'BCA'),
            ('Bachelor of Commerce', 'BCOM'),
            ('Master of Business Administration', 'MBA'),
        ]
        
        for dept_name, dept_code in departments_data:
            existing = Department.query.filter_by(code=dept_code).first()
            if not existing:
                dept = Department(name=dept_name, code=dept_code)
                db.session.add(dept)
                print(f"✓ Created department: {dept_code}")
            else:
                print(f"✓ Department already exists: {dept_code}")
        
        db.session.commit()
        
        print("\n" + "="*60)
        print("✓ DATABASE SETUP COMPLETE!")
        print("="*60)
        print("\n📋 Next Steps:")
        print("1. Run: python run.py")
        print("2. Open: http://localhost:5000")
        print("3. Login with:")
        print("   - Username: admin")
        print("   - Password: admin123")
        print("\n" + "="*60)

if __name__ == '__main__':
    init_database()
