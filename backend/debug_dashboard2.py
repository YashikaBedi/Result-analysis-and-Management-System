import traceback
from app import create_app, db
from app.models import User
from flask import current_app

app = create_app()

with app.app_context():
    # Attempt to run the dashboard function directly
    from app.routes import admin_bp
    dashboard_func = admin_bp.view_functions['dashboard']
    
    # We must mock flask_login's current_user to bypass @login_required / @admin_required
    import flask_login
    class MockUser:
        is_authenticated = True
        role = 'admin'
        
    flask_login.utils._get_user = lambda: MockUser()
    
    try:
        with app.test_request_context('/admin/'):
            flask_login.login_user(User.query.filter_by(username='admin').first())
            res = dashboard_func()
            print("Dashboard returned:", type(res))
            if hasattr(res, 'status_code'):
                print("Status code:", res.status_code)
                if res.status_code in (301, 302, 303):
                    print("Redirect Location:", res.headers.get('Location'))
    except Exception as e:
        print("EXCEPTION IN DASHBOARD:")
        traceback.print_exc()
