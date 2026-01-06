from aiohttp import web
import uuid
import logging

@web.middleware
async def request_id_middleware(request: web.Request, handler):
    """
    Middleware to inject a unique Request ID for traceability.
    """
    request_id = str(uuid.uuid4())
    request['request_id'] = request_id
    
    # Log entry (optional, helpful for debugging flow)
    # logging.debug(f"[Req {request_id}] Started {request.method} {request.path}")
    
    try:
        response = await handler(request)
        response.headers['X-Request-ID'] = request_id
        return response
    except Exception as e:
        # Log error with correlation ID
        logging.error(f"[Req {request_id}] Failed: {e}")
        raise e
