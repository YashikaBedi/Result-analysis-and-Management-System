from app import create_app, db
from app.models import Course, User

app = create_app()
with app.app_context():
    u = User.query.filter_by(username='hardik1').first()
    if not u:
        print("User hardik1 not found!")
    else:
        # Assign all courses to hardik1 for testing purposes
        courses = Course.query.all()
        for c in courses:
            c.faculty_id = u.id
            print(f"Assigned {c.course_code} to {u.username}")
        db.session.commit()
        print("Done!")
