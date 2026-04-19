import os
import sys

backend_dir = os.path.abspath(os.path.dirname(__file__))
print('DEBUG: backend_dir=', backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
print('DEBUG: sys.path set')

try:
    print('DEBUG: importing create_app')
    from app import create_app
    print('DEBUG: create_app imported')
    app = create_app('development')
    print('DEBUG: app created')
    print('APP_OK')
except Exception:
    import traceback
    traceback.print_exc()
