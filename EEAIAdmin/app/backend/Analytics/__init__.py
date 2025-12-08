"""
Analytics Module
Handles all analytics-related routes including dashboards, compliance analytics,
module performance metrics, and data export functionality
"""
from .analytics_routes import register_analytics_routes

__all__ = ['register_analytics_routes']
