from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        # Drop and recreate for simplicity in this demo environment if needed, 
        # but let's try to add columns first to be safe.
        engine = db.engine
        
        # Tables to create
        db.create_all()
        
        print("Database tables created/updated.")
        
        # Add columns manually if they don't exist
        with engine.connect() as conn:
            # Users table
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_requested BOOLEAN DEFAULT FALSE"))
                print("Added password_reset_requested to users")
            except Exception as e: print(f"Users table update skipped: {e}")

            # Courses table
            try:
                conn.execute(text("ALTER TABLE courses ADD COLUMN section VARCHAR(5) DEFAULT 'A'"))
                print("Added section to courses")
            except Exception as e: print(f"Courses table update skipped: {e}")

            # Students table
            try:
                conn.execute(text("ALTER TABLE students ADD COLUMN section VARCHAR(5) DEFAULT 'A'"))
                print("Added section to students")
            except Exception as e: print(f"Students table update skipped: {e}")

            # Results table updates
            new_result_cols = [
                "cie_1 FLOAT DEFAULT 0",
                "cie_2 FLOAT DEFAULT 0",
                "cie_3 FLOAT DEFAULT 0",
                "internal_exam_1 FLOAT DEFAULT 0",
                "internal_exam_2 FLOAT DEFAULT 0",
                "practical_file_marks FLOAT DEFAULT 0",
                "internal_practical_marks FLOAT DEFAULT 0"
            ]
            for col in new_result_cols:
                try:
                    conn.execute(text(f"ALTER TABLE results ADD COLUMN {col}"))
                    print(f"Added {col.split()[0]} to results")
                except Exception as e: print(f"Results table update skipped for {col.split()[0]}: {e}")

            # Remove old columns (optional, but requested to update Result model)
            # Actually, keeping them is safer as it won't crash existing code during transition
            
            conn.commit()
            print("Migration completed.")

if __name__ == "__main__":
    migrate()
