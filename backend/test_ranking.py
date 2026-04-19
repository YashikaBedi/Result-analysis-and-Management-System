import traceback
from app import create_app
from app.routes import get_department_ranking

app = create_app()
with app.app_context():
    try:
        get_department_ranking()
        print("SUCCESS")
    except Exception as e:
        print("ERROR:")
        traceback.print_exc()
