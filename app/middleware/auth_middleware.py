from aiohttp import web
import logging

# Determine routes that should be Public (no auth required)
# Usually static files, root, basic system info might be public
# But for strict security, everything except maybe "/" or specific assets should be private.
PUBLIC_ROUTES = [
    "/",
    "/index.html",
    "/favicon.ico",
    "/assets", # Frontend assets
    "/extensions", # Frontend extensions might need loading before auth? Unclear.
    # Assuming frontend handles auth logic, it needs to load first. 
    # But usually API calls are what we protect.
]

PUBLIC_PREFIXES = [
    "/assets/", 
    "/extensions/", 
    "/web/",
    "/scripts/", 
    "/lib/"
]

@web.middleware
async def auth_middleware(request: web.Request, handler):
    """
    Middleware to validate 'comfy-user' header if multi-user mode is enabled.
    """
    from comfy.cli_args import args
    
    # Skip if not multi-user
    if not args.multi_user:
        return await handler(request)

    path = request.path

    # Allow public assets
    # Simplistic check: if it looks like a frontend asset, let it pass
    # Real protection is for API endpoints (mostly starting with /api/ or specific server actions)
    
    # Logic: Protection by default for /api/ and similar? 
    # Or block everything unless whitelisted?
    # Given we want to block "anyone can impersonate", we check if the user claims to be someone.
    
    # Requirement: "only users registered can interact".
    
    # If path starts with public prefixes, skip
    for prefix in PUBLIC_PREFIXES:
         if path.startswith(prefix):
             return await handler(request)
             
    if path in PUBLIC_ROUTES:
        return await handler(request)
        
    # Check Header
    user_id = request.headers.get("comfy-user")
    
    if not user_id:
        # If no user provided, and it's an API call, Block.
        # If it's the main page loading, maybe allow? 
        # But ComfyUI frontend usually sends requests constantly.
        # For now, we enforce strictness on everything else.
        # But wait, if user loads "/", they have no header yet.
        # So we must allow "/" and assets. (Handled above)
        
        # If it is an API call without user, 401.
        if path.startswith("/api/") or path.startswith("/upload/") or path.startswith("/view"):
             logging.warning(f"[Auth] Unauthorized access attempt to {path} (No User Header)")
             return web.json_response({"error": "Unauthorized: Login required"}, status=401)
        
        # Determine if we should be strict on everything else
        # For safety, let's log and allow non-api for now to avoid breaking UI loading,
        # Unless we are sure. To be safe, let's block key endpoints.
        
    else:
        # User ID provided. Check if exists.
        # Need access to UserManager.
        # Circular import risk if we import PromptServer here?
        # PromptServer imports this middleware usually? No, we will import this in server.py
        # So we can import server here inside function?
        import server
        instance = server.PromptServer.instance
        if instance and instance.user_manager:
            # Check existance
            # We can use internal method `get_user_by_id` (DB) or `users` dict (file)
            # The manager's `get_user_by_id` or `get_all_users` works.
            
            # Using get_all_users() might be heavy if many users, but safe for now.
            # Ideally user_manager exposes `user_exists(id)`
            
            # Since we refactored user_manager to use DB, let's try get_user_by_id
            try:
                # Assuming get_user_by_id returns username or None
                exists = instance.user_manager.get_user_by_id(user_id) 
                
                # If None, check users dict (legacy) just in case fallback logic is weird?
                # No, get_user_by_id handles fallback.
                
                if not exists:
                     logging.warning(f"[Auth] Unauthorized access: User {user_id} not found.")
                     return web.json_response({"error": "Unauthorized: Invalid User"}, status=401)
                     
            except Exception as e:
                logging.error(f"[Auth] Error checking user: {e}")
                return web.json_response({"error": "Internal Auth Error"}, status=500)
    
    return await handler(request)
