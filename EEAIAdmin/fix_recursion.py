"""
Temporary fix for RecursionError in Flask app
Run this script to test if the app works without template includes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Patch the template rendering to ignore missing includes
from jinja2 import TemplateNotFound
from flask import Flask, render_template as original_render_template

def safe_render_template(template_name, **context):
    """Safely render template with fallback for missing includes"""
    try:
        return original_render_template(template_name, **context)
    except TemplateNotFound as e:
        print(f"Template not found: {e}")
        # Return a simple error page
        return f"""
        <html>
        <body>
            <h1>Template Error</h1>
            <p>Could not load template: {template_name}</p>
            <p>Error: {str(e)}</p>
            <a href="/">Go to Home</a>
        </body>
        </html>
        """
    except RecursionError:
        print(f"RecursionError while rendering {template_name}")
        return f"""
        <html>
        <body>
            <h1>Recursion Error</h1>
            <p>A recursion error occurred while loading: {template_name}</p>
            <a href="/">Go to Home</a>
        </body>
        </html>
        """

# Monkey patch render_template
import flask
flask.render_template = safe_render_template

# Now import and run the app
from app import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=False)