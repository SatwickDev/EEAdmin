"""
Database Connection Routes for Flask

Provides API endpoints for managing database connections in the LC Management System.

Endpoints:
    GET    /api/database/connections              - List all connections
    GET    /api/database/connections/<name>       - Get connection details
    POST   /api/database/connections/<name>/test  - Test connection
    POST   /api/database/connections/<name>/default - Set as default
    POST   /api/database/connections              - Add new connection
    PUT    /api/database/connections/<name>       - Update connection
    DELETE /api/database/connections/<name>       - Delete connection
"""

from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime
from .database_connection_manager import DatabaseConnectionManager

# Create Blueprint
database_bp = Blueprint('database', __name__)

# Initialize connection manager
CONFIG_FILE = 'database_connections.json'
manager = DatabaseConnectionManager(CONFIG_FILE)


@database_bp.route('/api/database/connections', methods=['GET'])
def list_connections():
    """
    List all database connections
    
    Returns:
        {
            "success": true,
            "connections": [
                {
                    "name": "mongodb_local",
                    "display_name": "MongoDB Local",
                    "type": "mongodb",
                    "description": "...",
                    "status": "active",
                    "is_default": true,
                    "is_active": true
                }
            ],
            "count": 7
        }
    """
    try:
        connections = manager.list_connections()
        return jsonify({
            'success': True,
            'connections': connections,
            'count': len(connections)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/api/database/connections/<connection_name>', methods=['GET'])
def get_connection_details(connection_name):
    """
    Get detailed information about a specific connection
    
    Returns:
        {
            "success": true,
            "connection": {
                "name": "mongodb_local",
                "display_name": "MongoDB Local",
                "type": "mongodb",
                "config": {...},
                "is_default": true,
                "is_active": true
            }
        }
    """
    try:
        info = manager.get_connection_info(connection_name)
        
        if info:
            return jsonify({
                'success': True,
                'connection': info
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Connection "{connection_name}" not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/api/database/connections/<connection_name>/test', methods=['POST'])
def test_connection(connection_name):
    """
    Test a database connection
    
    Returns:
        {
            "success": true,
            "connection_name": "mongodb_local",
            "message": "Connection successful",
            "timestamp": "2024-01-01T12:00:00"
        }
    """
    try:
        result = manager.test_connection(connection_name)
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'connection_name': connection_name,
            'message': f'Test failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@database_bp.route('/api/database/connections/<connection_name>/default', methods=['POST'])
def set_default_connection(connection_name):
    """
    Set a connection as the default
    
    Returns:
        {
            "success": true,
            "message": "Connection set as default"
        }
    """
    try:
        # Load current config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Check if connection exists
        if connection_name not in config['connections']:
            return jsonify({
                'success': False,
                'error': f'Connection "{connection_name}" not found'
            }), 404
        
        # Update is_default flag
        for conn_name, conn_config in config['connections'].items():
            conn_config['is_default'] = (conn_name == connection_name)
        
        # Update metadata
        config['metadata']['updated_at'] = datetime.now().isoformat()
        
        # Save config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Reload manager
        manager.load_config()
        
        return jsonify({
            'success': True,
            'message': f'Connection "{connection_name}" set as default'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/api/database/connections', methods=['POST'])
def add_connection():
    """
    Add a new database connection
    
    Request Body:
        {
            "name": "mongodb_prod",
            "display_name": "MongoDB Production",
            "type": "mongodb",
            "description": "Production MongoDB instance",
            "config": {
                "host": "prod.example.com",
                "port": 27017,
                "database": "lc_management"
            },
            "status": "active"
        }
    
    Returns:
        {
            "success": true,
            "message": "Connection added successfully"
        }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'display_name', 'type', 'config']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Load current config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Check if connection already exists
        if data['name'] in config['connections']:
            return jsonify({
                'success': False,
                'error': f'Connection "{data["name"]}" already exists'
            }), 409
        
        # Add new connection
        config['connections'][data['name']] = {
            'name': data['display_name'],
            'type': data['type'],
            'description': data.get('description', ''),
            'config': data['config'],
            'status': data.get('status', 'active'),
            'is_default': data.get('is_default', False)
        }
        
        # Update metadata
        config['metadata']['updated_at'] = datetime.now().isoformat()
        
        # Save config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Reload manager
        manager.load_config()
        
        return jsonify({
            'success': True,
            'message': f'Connection "{data["name"]}" added successfully'
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/api/database/connections/<connection_name>', methods=['PUT'])
def update_connection(connection_name):
    """
    Update an existing database connection
    
    Request Body:
        {
            "display_name": "MongoDB Production Updated",
            "config": {
                "host": "new-host.example.com"
            }
        }
    
    Returns:
        {
            "success": true,
            "message": "Connection updated successfully"
        }
    """
    try:
        data = request.get_json()
        
        # Load current config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Check if connection exists
        if connection_name not in config['connections']:
            return jsonify({
                'success': False,
                'error': f'Connection "{connection_name}" not found'
            }), 404
        
        # Update connection
        conn = config['connections'][connection_name]
        
        if 'display_name' in data:
            conn['name'] = data['display_name']
        if 'description' in data:
            conn['description'] = data['description']
        if 'config' in data:
            conn['config'].update(data['config'])
        if 'status' in data:
            conn['status'] = data['status']
        
        # Update metadata
        config['metadata']['updated_at'] = datetime.now().isoformat()
        
        # Save config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Reload manager and close old connection
        manager.close_connection(connection_name)
        manager.load_config()
        
        return jsonify({
            'success': True,
            'message': f'Connection "{connection_name}" updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/api/database/connections/<connection_name>', methods=['DELETE'])
def delete_connection(connection_name):
    """
    Delete a database connection
    
    Returns:
        {
            "success": true,
            "message": "Connection deleted successfully"
        }
    """
    try:
        # Load current config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Check if connection exists
        if connection_name not in config['connections']:
            return jsonify({
                'success': False,
                'error': f'Connection "{connection_name}" not found'
            }), 404
        
        # Don't allow deleting default connection
        if config['connections'][connection_name].get('is_default', False):
            return jsonify({
                'success': False,
                'error': 'Cannot delete default connection. Set another connection as default first.'
            }), 400
        
        # Delete connection
        del config['connections'][connection_name]
        
        # Update metadata
        config['metadata']['updated_at'] = datetime.now().isoformat()
        
        # Save config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Close connection if active and reload manager
        manager.close_connection(connection_name)
        manager.load_config()
        
        return jsonify({
            'success': True,
            'message': f'Connection "{connection_name}" deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_bp.route('/api/database/default', methods=['GET'])
def get_default_connection():
    """
    Get the default database connection
    
    Returns:
        {
            "success": true,
            "connection": {
                "name": "mongodb_local",
                "display_name": "MongoDB Local",
                "type": "mongodb",
                ...
            }
        }
    """
    try:
        connections = manager.list_connections()
        default_conn = next((c for c in connections if c['is_default']), None)
        
        if default_conn:
            return jsonify({
                'success': True,
                'connection': default_conn
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No default connection configured'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Cleanup on app shutdown
def cleanup_connections():
    """Close all database connections"""
    try:
        manager.close_all_connections()
    except Exception as e:
        print(f"Error closing connections: {e}")


# Register cleanup handler
import atexit
atexit.register(cleanup_connections)
