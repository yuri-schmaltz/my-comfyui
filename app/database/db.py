import logging
import os
import shutil
from app.logger import log_startup_warning
from utils.install_util import get_missing_requirements_message
from comfy.cli_args import args

_DB_AVAILABLE = False
Session = None


try:
    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    _DB_AVAILABLE = True
except ImportError as e:
    log_startup_warning(
        f"""
------------------------------------------------------------------------
Error importing dependencies: {e}
{get_missing_requirements_message()}
This error is happening because ComfyUI now uses a local sqlite database.
------------------------------------------------------------------------
""".strip()
    )


def dependencies_available():
    """
    Temporary function to check if the dependencies are available
    """
    return _DB_AVAILABLE


def can_create_session():
    """
    Temporary function to check if the database is available to create a session
    During initial release there may be environmental issues (or missing dependencies) that prevent the database from being created
    """
    return dependencies_available() and Session is not None


def get_alembic_config():
    root_path = os.path.join(os.path.dirname(__file__), "../..")
    config_path = os.path.abspath(os.path.join(root_path, "alembic.ini"))
    scripts_path = os.path.abspath(os.path.join(root_path, "alembic_db"))

    config = Config(config_path)
    config.set_main_option("script_location", scripts_path)
    config.set_main_option("sqlalchemy.url", args.database_url)

    return config


def get_db_path():
    url = args.database_url
    if url.startswith("sqlite:///"):
        return url.split("///")[1]
    else:
        raise ValueError(f"Unsupported database URL '{url}'.")


from .models import Base, User
import json
import folder_paths

def init_db():
    if not dependencies_available():
        logging.info("Running in File-Based Mode (DB dependencies missing). persistence via JSON.")
        return

    db_url = args.database_url
    logging.debug(f"Database URL: {db_url}")
    
    # Create engine
    engine = create_engine(db_url)
    
    # Create tables (No-op if exist)
    Base.metadata.create_all(engine)
    
    global Session
    Session = sessionmaker(bind=engine)
    
    # Auto-Migration: JSON -> SQLite
    session = Session()
    try:
        # Check if DB is empty
        try:
            user_count = session.query(User).count()
        except Exception:
            user_count = 0
            
        if user_count == 0:
            user_file = os.path.join(folder_paths.get_user_directory(), "users.json")
            if os.path.exists(user_file):
                logging.info("[DB] Database empty. Migrating users from JSON...")
                try:
                    with open(user_file, 'r') as f:
                        users_data = json.load(f)
                        
                    if isinstance(users_data, dict):
                        count = 0
                        for uid, uname in users_data.items():
                            # Avoid duplicates just in case
                            if not session.query(User).filter_by(id=uid).first():
                                user = User(id=str(uid), username=str(uname))
                                session.add(user)
                                count += 1
                        session.commit()
                        logging.info(f"[DB] Successfully migrated {count} users.")
                    else:
                        logging.warning("[DB] users.json format unexpected. Skipping.")
                except Exception as e:
                    logging.error(f"[DB] Migration failed: {e}")
    except Exception as e:
        logging.error(f"[DB] Initialization error: {e}")
    finally:
        session.close()

    create_session = Session
