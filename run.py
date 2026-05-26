import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())
import main
main.init_database()
main.CONFIG["USE_HTTPS"] = False
main.app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)
