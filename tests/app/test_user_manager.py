import unittest
import json
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
import sys

# Ensure root path is in sys.path
sys.path.append(os.getcwd())

# MOCKING DEPENDENCIES
sys.modules["aiohttp"] = MagicMock()
sys.modules["aiohttp.web"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()
sys.modules["sqlalchemy.orm"] = MagicMock()
sys.modules["app.database.models"] = MagicMock() # Mock models too to avoid import errors if needed

from app import user_manager

class TestUserManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for user data
        self.test_dir = tempfile.mkdtemp()
        self.user_dir = os.path.join(self.test_dir, "user_data")
        os.makedirs(self.user_dir, exist_ok=True)
        
        # Patch folder_paths
        self.patcher_paths = patch('app.user_manager.folder_paths')
        self.mock_paths = self.patcher_paths.start()
        self.mock_paths.get_user_directory.return_value = self.user_dir
        self.mock_paths.SYSTEM_USER_PREFIX = "system"
        
        # Patch args
        self.patcher_args = patch('app.user_manager.args')
        self.mock_args = self.patcher_args.start()
        self.mock_args.multi_user = True 
        
    def tearDown(self):
        self.patcher_paths.stop()
        self.patcher_args.stop()
        shutil.rmtree(self.test_dir)

    def test_fallback_add_user(self):
        """Test fallback to file when DB is unavailable"""
        with patch('app.user_manager.db') as mock_db:
             mock_db.dependencies_available.return_value = False
             
             manager = user_manager.UserManager()
             user_id = manager.add_user("fallback_user")
             
             # Check users file path
             users_file = os.path.join(self.user_dir, "users.json")
             self.assertTrue(os.path.exists(users_file))
             
             with open(users_file, 'r') as f:
                 data = json.load(f)
             
             self.assertIn(user_id, data)
             self.assertEqual(data[user_id], "fallback_user")

    def test_db_add_user(self):
        """Test saving to DB when available"""
        with patch('app.user_manager.db') as mock_db:
             mock_db.dependencies_available.return_value = True
             mock_session = MagicMock()
             mock_db.create_session.return_value = mock_session
             
             # Configure User mock to behave like an object
             def user_constructor(id, username):
                 m = MagicMock()
                 m.id = id
                 m.username = username
                 return m
             
             user_manager.User.side_effect = user_constructor
             
             manager = user_manager.UserManager()
             user_id = manager.add_user("db_user")
             
             # Verify session interactions
             mock_db.create_session.assert_called()
             mock_session.add.assert_called()
             mock_session.commit.assert_called()
             
             # Extract the user object added
             args, _ = mock_session.add.call_args
             user_obj = args[0]
             self.assertEqual(user_obj.username, "db_user")
             self.assertEqual(user_obj.id, user_id)
             
             # Ensure NO file write happened (fallback skipped)
             users_file = os.path.join(self.user_dir, "users.json")
             self.assertFalse(os.path.exists(users_file))

    def test_get_user_db(self):
        """Test retrieving user from DB"""
        with patch('app.user_manager.db') as mock_db:
             mock_db.dependencies_available.return_value = True
             mock_session = MagicMock()
             mock_db.create_session.return_value = mock_session
             
             # Mock query return
             mock_user = MagicMock()
             mock_user.username = "found_user"
             mock_session.query.return_value.filter.return_value.first.return_value = mock_user
             
             manager = user_manager.UserManager()
             username = manager.get_user_by_id("some_id")
             
             self.assertEqual(username, "found_user")

if __name__ == '__main__':
    unittest.main()
