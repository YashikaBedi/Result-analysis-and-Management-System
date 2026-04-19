from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    u = User.query.filter_by(username='admin').first()
    print(f"User admin exists: {u is not None}")
    if u:
        print(f"Password valid for admin123: {u.check_password('admin123')}")
        print(f"Role: {u.role}")
