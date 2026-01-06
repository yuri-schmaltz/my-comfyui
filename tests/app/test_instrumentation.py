import unittest
from unittest.mock import MagicMock, patch, AsyncMock

import sys
import os
import json

# Ensure root path is in sys.path
sys.path.append(os.getcwd())

# MOCKING DEPENDENCIES (Copy from previous tests for consistency)
aiohttp_mock = MagicMock()
web_mock = MagicMock()
sys.modules["aiohttp"] = aiohttp_mock
sys.modules["aiohttp.web"] = web_mock
aiohttp_mock.web = web_mock
sys.modules["aiohttp.web"].middleware = lambda f: f

def mock_json_response(data, status=200):
   resp = MagicMock()
   resp.status = status
   
   # Store data as attribute to inspect it in tests
   # In real aiohttp this renders to body bytes, here we keep the dict/obj
   resp._debug_body = data 
   return resp
sys.modules["aiohttp.web"].json_response = mock_json_response

# Fake RouteTableDef to capture routes
class FakeRouteTableDef:
    def __init__(self):
        self._routes = []
    
    def get(self, path):
        def decorator(handler):
            self._routes.append(MagicMock(path=path, handler=handler))
            return handler
        return decorator
    
    def patch(self, path):
        def decorator(handler):
            self._routes.append(MagicMock(path=path, handler=handler))
            return handler
        return decorator

    @property
    def routes(self): # Allow iteration over self.routes in test
        return self._routes
    
    def __iter__(self):
        return iter(self._routes)

sys.modules["aiohttp.web"].RouteTableDef = FakeRouteTableDef

# Now imports that use aiohttp
from aiohttp import web
from app.middleware.request_id_middleware import request_id_middleware

class TestInstrumentation(unittest.IsolatedAsyncioTestCase):
    async def test_request_id_middleware(self):
        """Test Request ID injection"""
        request = MagicMock()
        request.headers = {}
        request.__setitem__ = MagicMock() # Allow dictionary assignment
        
        # Mock response object
        response = MagicMock()
        response.headers = {}
        
        handler = AsyncMock(return_value=response)
        
        # Determine if request_id_middleware calls handler
        res = await request_id_middleware(request, handler)
        
        # Verify header injection
        self.assertIn("X-Request-ID", res.headers)
        self.assertTrue(res.headers["X-Request-ID"]) # Not empty

    async def test_metrics_endpoint(self):
        """Test /metrics route logic"""
        # We need to import InternalRoutes (it was modified)
        # We need to mock what InternalRoutes imports (folder_paths, app.logger)
        
        # Mocking at the source (before importing internal_routes) seems safer given the structure
        # But sys.modules works too.
        sys.modules["folder_paths"] = MagicMock()
        sys.modules["api_server.services.terminal_service"] = MagicMock()

        # We also need to patch app.logger at system level before import
        sys.modules["app"] = MagicMock() 
        sys.modules["app.logger"] = MagicMock()
        
        # Now import
        from api_server.routes.internal.internal_routes import InternalRoutes

        # Mock PromptServer
        mock_server = MagicMock()
        mock_server.number = 42
        mock_server.prompt_queue.get_current_queue.return_value = (["job1"], ["job2", "job3"])
             
        routes = InternalRoutes(mock_server)
        routes.setup_routes() 
        
        # We need to find the metrics handler in the registry
        # routes.routes is a RouteTableDef.
        # We can iterate to find '/metrics'
        metrics_handler = None
        for route in routes.routes:
            if route.path == '/metrics':
                metrics_handler = route.handler
                break
    
        self.assertIsNotNone(metrics_handler, "Metrics route not found")
        
        # Execute handler
        request = MagicMock()
        response = await metrics_handler(request)
        
        data = response._debug_body
        self.assertEqual(data["queue_running"], 1)
        self.assertEqual(data["queue_pending"], 2)
        self.assertEqual(data["job_count"], 42)

if __name__ == '__main__':
    unittest.main()
