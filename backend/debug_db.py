from app import create_app, db
from app.models import Course, User

app = create_app()
with app.app_context():
    users = User.query.all()
    print("USER ROLES IN DATABASE:")
    for u in users:
        print(f" - ID: {u.id} | Username: {u.username} | Role: '{u.role}'")
    
    courses = Course.query.all()
    print(f"\nTOTAL COURSES: {len(courses)}")
