import unittest
from unittest.mock import MagicMock, patch, AsyncMock

import sys
import os

# Ensure root path is in sys.path
sys.path.append(os.getcwd())

# MOCKING DEPENDENCIES
aiohttp_mock = MagicMock()
web_mock = MagicMock()
sys.modules["aiohttp"] = aiohttp_mock
sys.modules["aiohttp.web"] = web_mock
aiohttp_mock.web = web_mock # CRITICAL LINK
# Mock web.middleware decorator which is used at import time
sys.modules["aiohttp.web"].middleware = lambda f: f
# Mock json_response
def mock_json_response(data, status=200):
   resp = MagicMock()
   resp.status = status
   resp.body = data
   return resp
sys.modules["aiohttp.web"].json_response = mock_json_response

# Mock server module (to avoid import chains like torch_directml)
sys.modules["server"] = MagicMock()

from app.middleware.auth_middleware import auth_middleware


class TestAuthMiddleware(unittest.IsolatedAsyncioTestCase):
    async def test_public_route_passthrough(self):
        """Test that public routes are bypassed"""
        request = MagicMock()
        request.path = "/index.html"
        request.headers = {}
        
        handler = AsyncMock(return_value="OK")
        
        # Patch args.multi_user = True
        with patch('comfy.cli_args.args') as mock_args:
            mock_args.multi_user = True
            
            response = await auth_middleware(request, handler)
            self.assertEqual(response, "OK") # Passes through

    async def test_no_header_block(self):
        """Test blocking API route without header"""
        request = MagicMock()
        request.path = "/api/jobs"
        request.headers = {}
        
        handler = AsyncMock()
        
        with patch('comfy.cli_args.args') as mock_args:
            mock_args.multi_user = True
            
            response = await auth_middleware(request, handler)
            
            # Should block
            self.assertNotEqual(response, "OK")
            self.assertEqual(response.status, 401)

    async def test_invalid_user_block(self):
        """Test blocking invalid user"""
        request = MagicMock()
        request.path = "/api/jobs"
        request.headers = {"comfy-user": "hacker"}
        
        handler = AsyncMock()
        
        with patch('comfy.cli_args.args') as mock_args:
            mock_args.multi_user = True
            
            # Mock Server instance
            with patch('server.PromptServer') as MockServer:
                instance = MockServer.instance
                # Mock user manager saying user does not exist
                instance.user_manager.get_user_by_id.return_value = None 
                
                response = await auth_middleware(request, handler)
                self.assertEqual(response.status, 401)

    async def test_valid_user_pass(self):
        """Test passing valid user"""
        request = MagicMock()
        request.path = "/api/jobs"
        request.headers = {"comfy-user": "valid_user"}
        
        handler = AsyncMock(return_value="OK")
        
        with patch('comfy.cli_args.args') as mock_args:
            mock_args.multi_user = True
            
            with patch('server.PromptServer') as MockServer:
                instance = MockServer.instance
                instance.user_manager.get_user_by_id.return_value = "valid_user"
                
                response = await auth_middleware(request, handler)
                self.assertEqual(response, "OK")

if __name__ == '__main__':
    unittest.main()
