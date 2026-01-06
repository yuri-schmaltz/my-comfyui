import logging
import sys
import os

# Filter warnings before importing db which might trigger them
os.environ['PYTHONWARNINGS'] = 'ignore'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from app.database import db
    print("Imported db module successfully.")
    
    # Mock args if needed, or rely on defaults. 
    # db.py uses 'comfy.cli_args.args'
    # We might need to mock that if it's not initialized.
    from comfy.cli_args import args
    args.database_url = "sqlite:///databaserefcheck.db" # Dummy URL
    
    # Mock get_alembic_config because we don't want to rely on real file if it fails deeper
    # But we WANT to test the file persistence check.
    # The code checks: os.path.join(os.path.dirname(get_alembic_config().get_main_option("script_location")), "versions")
    
    db.init_db()
    print("init_db() returned successfully.")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
