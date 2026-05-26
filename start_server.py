import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app, init_database
init_database()
app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)
