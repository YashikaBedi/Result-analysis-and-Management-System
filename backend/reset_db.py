import os
import sys
# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db

def reset_db():
    app = create_app()
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        print("Database reset successfully.")

if __name__ == "__main__":
    reset_db()
