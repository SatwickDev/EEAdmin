"""
Admin Configuration Module
===========================

This module provides comprehensive admin configuration functionality
for managing entities, categories, mappings, and prompt configurations.

Key Components:
- DataCategoryManager: Manages data categories CRUD operations
- EntityManager: Manages entity definitions CRUD operations
- DocumentCategoryManager: Manages document categories CRUD operations (JSON)
- DocumentTypeCategoryManager: Manages document type categories CRUD operations (YAML)
- DocumentEntityMappingManager: Manages document-entity field mappings
- PromptConfigManager: Manages LLM prompt configurations

Usage:
    from app.backend.Admin_Configuraton import (
        DataCategoryManager,
        EntityManager,
        DocumentCategoryManager,
        DocumentTypeCategoryManager,
        DocumentEntityMappingManager,
        PromptConfigManager
    )
"""

import logging

logger = logging.getLogger(__name__)

# Import managers
from .data_category_manager import DataCategoryManager
from .entity_manager import EntityManager
from .document_category_manager import DocumentCategoryManager
from .document_type_category_manager import DocumentTypeCategoryManager
from .document_entity_mapping_manager import DocumentEntityMappingManager
from .prompt_config_manager import PromptConfigManager

# Import route registration
from .admin_config_routes import register_admin_config_routes

# Export all components
__all__ = [
    'DataCategoryManager',
    'EntityManager',
    'DocumentCategoryManager',
    'DocumentTypeCategoryManager',
    'DocumentEntityMappingManager',
    'PromptConfigManager',
    'register_admin_config_routes'
]

logger.info("✅ Admin Configuration module initialized")
