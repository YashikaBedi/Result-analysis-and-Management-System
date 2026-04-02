#!/usr/bin/env python
"""Application entry point"""

import os
from app import create_app, db

# Create application instance
app = create_app()

# Shell context for flask shell
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': __import__('app.models', fromlist=['User']).User,
        'Student': __import__('app.models', fromlist=['Student']).Student,
        'Department': __import__('app.models', fromlist=['Department']).Department,
        'Course': __import__('app.models', fromlist=['Course']).Course,
        'Result': __import__('app.models', fromlist=['Result']).Result,
    }

if __name__ == '__main__':
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
