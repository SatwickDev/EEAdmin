"""
Example of how to integrate clean_routes.py into your Flask app
"""

# In your main app file or __init__.py, add:

from app.clean_routes import clean_routes_bp

def register_clean_routes(app):
    """Register the clean routes blueprint with the Flask app"""
    # Register the blueprint
    app.register_blueprint(clean_routes_bp)
    
    # Or register with a URL prefix if you want all routes under a specific path
    # app.register_blueprint(clean_routes_bp, url_prefix='/api/v2')

# Then in your app initialization:
# app = create_app()
# register_clean_routes(app)

# Note: Since you already have session routes in routes.py that duplicate this functionality,
# you should choose one implementation to avoid conflicts:
# 1. Use clean_routes.py and remove the session routes from routes.py
# 2. Keep routes.py as is and don't use clean_routes.py
# 3. Use clean_routes.py with a different URL prefix (e.g., /api/v2/sessions)