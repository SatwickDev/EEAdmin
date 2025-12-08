"""
Guarantee Vetting Module

This module handles all guarantee vetting functionality including:

1. Guarantee Vetting Rules (JSON-based):
   - Guarantee vetting rules management (whitelist/blacklist)
   - AI-powered rule generation and analysis
   - Blacklist rules CRUD operations
   - Whitelist rules CRUD operations
   - Guarantee prompt configuration
   - Rule preview and testing
   - Routes: /api/guarantee_vetting_rules/*, /api/blacklist_rules/*, /api/whitelist_rules/*

2. Vetting Rule Engine (MongoDB-based):
   - VettingRuleEngine integration for rule management
   - Admin-only rule CRUD operations
   - AI-powered test sample generation
   - Rule effectiveness analysis
   - Guarantee terms vetting
   - Routes: /api/vetting/*
"""

from .vetting_rules_helpers import (
    load_guarantee_vetting_rules,
    save_guarantee_vetting_rules
)

from .guarantee_vetting_routes import register_guarantee_vetting_routes
from .vetting_rule_engine_routes import register_vetting_rule_engine_routes
from .guarantee_submission_routes import register_guarantee_submission_routes

__all__ = [
    'register_guarantee_vetting_routes',
    'register_vetting_rule_engine_routes',
    'register_guarantee_submission_routes',
    'load_guarantee_vetting_rules',
    'save_guarantee_vetting_rules'
]
