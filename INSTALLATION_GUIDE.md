# College Exam Result Management System - Installation Guide

## Quick Start Guide

Follow these steps to get the application running on your system.

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.8 or higher**
   - Download from: https://www.python.org/downloads/
   - Verify: `python --version`

2. **PostgreSQL 12 or higher**
   - Download from: https://www.postgresql.org/download/
   - Verify: `psql --version`

3. **Git** (optional, for cloning repository)
   - Download from: https://git-scm.com/

## Installation Steps

### 1. Navigate to Project Directory

```bash
cd Desktop/college_exam_system
```

### 2. Create Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- Flask and extensions
- SQLAlchemy (ORM)
- PostgreSQL driver
- Science libraries (Pandas, NumPy)
- Visualization tools (Matplotlib, Plotly)
- PDF generation (ReportLab)

### 4. Configure Database

#### Step 4.1: Create Database User and Database

**On Windows (psql client):**
```sql
-- Open psql
psql -U postgres

-- Create database user
CREATE USER college_user WITH PASSWORD 'college_password';

-- Create database
CREATE DATABASE college_exam_system OWNER college_user;

-- Grant privileges
ALTER ROLE college_user SET client_encoding TO 'utf8';
ALTER ROLE college_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE college_user SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE college_exam_system TO college_user;

-- Exit
\q
```

#### Step 4.2: Update Environment Variables

Edit `.env` file and update:
```
DATABASE_URL=postgresql://college_user:college_password@localhost:5432/college_exam_system
SECRET_KEY=your-unique-secret-key-here
```

### 5. Initialize the Database

```bash
flask init-db
```

Or use Python:
```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 6. Create Admin User (Optional but Recommended)

```bash
python
>>> from app import create_app, db
>>> from app.models import User
>>> app = create_app()
>>> with app.app_context():
...     admin = User(
...         username='admin',
...         email='admin@college.edu',
...         full_name='System Administrator',
...         role='admin'
...     )
...     admin.set_password('admin123')
...     db.session.add(admin)
...     db.session.commit()
...     print('Admin user created successfully!')
>>> exit()
```

### 7. Run the Application

```bash
python run.py
```

The application will start on `http://localhost:5000`

## Login

Use the credentials created in step 6:
- **Username**: admin
- **Password**: admin123

## Creating Demo Data

### Create Department

As Admin:
1. Go to Admin Panel
2. Click "Manage Departments"
3. Click "Create Department"
4. Add department details:
   - Name: Master of Computer Application
   - Code: MCA

### Register Faculty

1. Logout and go to Register page
2. Create account with role "Faculty"
3. Complete registration
4. Faculty can now add marks

### Register Student

1. Register with role "Student"
2. Complete student profile with:
   - Registration number
   - Department
   - Admission year
3. View dashboard

## Troubleshooting

### Issue: PostgreSQL Connection Error

**Solution:**
1. Verify PostgreSQL is running:
   ```bash
   psql -U postgres
   ```
2. Check DATABASE_URL in `.env` file
3. Ensure credentials are correct
4. Verify database exists:
   ```sql
   \l
   ```

### Issue: "ModuleNotFoundError"

**Solution:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Issue: "Port 5000 already in use"

**Solution:**
```bash
# Check what's using port 5000
netstat -ano | findstr :5000

# Run on different port
python run.py --port 5001
```

### Issue: Template Not Found

**Solution:**
- Verify all files in `app/templates/` exist
- Check template directory structure matches references in HTML files
- Verify file paths use forward slashes `/` even on Windows

## Performance Tips

1. **Database Indexing**: Already configured in models
2. **Pagination**: Implemented for large datasets (20 items per page)
3. **Lazy Loading**: Used for relationships to avoid N+1 queries
4. **Caching**: Can be added for frequently accessed analytics

## Security Checklist

Before deployment to production:

- [ ] Change SECRET_KEY in `.env`
- [ ] Set FLASK_ENV to production
- [ ] Enable HTTPS
- [ ] Set database password to strong value
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Set up regular backups
- [ ] Configure email notifications
- [ ] Review user permissions

## Deployment

### Using Gunicorn (Production WSGI Server)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

### Using Docker (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "run:app"]
```

Build and run:
```bash
docker build -t college-exam-system .
docker run -p 8000:8000 college-exam-system
```

## Support Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Bootstrap Documentation**: https://getbootstrap.com/docs/

## Next Steps

1. Configure your institution settings
2. Create departments and programs
3. Register faculty members
4. Register students
5. Start entering exam results
6. Generate analytics reports

## Contact

For issues or questions, please contact your IT support team.

---

**Version**: 1.0.0
**Last Updated**: April 2026
