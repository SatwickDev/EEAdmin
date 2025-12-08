"""
Document Validation Service Module

This module provides the main validation service for validating document types
against predefined lists, mapping aliases, and filtering duplicates.

Step 4.1: Validates document types against predefined list
Step 4.2: Filters duplicate document types
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# DOCUMENT TYPE ALIASES CONFIGURATION
# ============================================================================
# Maps commonly misclassified or alternate names to standard document types

DOCUMENT_TYPE_ALIASES = {
    # Weight/Certificate mappings
    'Weight List': 'Certificate of Weight',
    'weight list': 'Certificate of Weight',
    'Weight Certificate': 'Certificate of Weight',
    'Weighing Certificate': 'Certificate of Weight',
    
    # Certificate of Origin mappings
    'Certificate Of Origin': 'Preferential Certificate of Origin',
    'certificate of origin': 'Preferential Certificate of Origin',
    'Certificate of Origin': 'Preferential Certificate of Origin',
    'COO': 'Preferential Certificate of Origin',
    'Origin Certificate': 'Preferential Certificate of Origin',
    
    # Insurance document mappings
    'Marine Insurance policy': 'Cargo Insurance Document',
    'Marine Insurance Policy': 'Cargo Insurance Document',
    'marine insurance policy': 'Cargo Insurance Document',
    'Shipment Consignment Advice': 'Cargo Insurance Document',
    'shipment consignment advice': 'Cargo Insurance Document',
    'Shipment consignment advice': 'Cargo Insurance Document',
    'shipment Consignment Advice': 'Cargo Insurance Document',
    'Insurance Consignment Advice': 'Cargo Insurance Document',
    'insurance consignment advice': 'Cargo Insurance Document',
    'Insurance consignment advice': 'Cargo Insurance Document',
    'insurance Consignment Advice': 'Cargo Insurance Document',
    'Insurance Advice': 'Cargo Insurance Document',
    'insurance Advice': 'Cargo Insurance Document',
    'Insurance advice': 'Cargo Insurance Document',
    'insurance advice': 'Cargo Insurance Document',
    
    # Vessel Certificate mappings
    'Certificate from Ship-Owner': 'Vessel Certificate',
    'certificate from ship-owner': 'Vessel Certificate',
    'Certificate From Ship-Owner': 'Vessel Certificate',
    'Certificate from Ship Owner': 'Vessel Certificate',
    'certificate from ship owner': 'Vessel Certificate',
    'Certificate From Ship Owner': 'Vessel Certificate',
    'certificate from Ship-OwneR': 'Vessel Certificate',
    'CERTIFICATE FROM SHIP OWNER': 'Vessel Certificate',
    'Certificate from Ship-Owner or Vessel Agent': 'Vessel Certificate',
    'certificate from ship-owner or vessel agent': 'Vessel Certificate',
    'Certificate from Ship-owner or Agent': 'Vessel Certificate',
    'certificate from ship-owner or agent': 'Vessel Certificate',
    'certificate from ship-owner': 'Vessel Certificate',
    'Certificate from Ship-Owner': 'Vessel Certificate',
    'Certificate From Ship-Owner': 'Vessel Certificate',
    'certificate From Ship-Owner': 'Vessel Certificate',
    'certificate from Ship-Owner': 'Vessel Certificate',
    'certificate from ship-Owner': 'Vessel Certificate',
    'Certificate from ship-Owner': 'Vessel Certificate',
    'CERTIFICATE FROM SHIP-OWNER': 'Vessel Certificate',
    
    # Inspection/Quality certificate mappings
    'Mill Certificate': 'Certificate of Inspection for Organic Products',
    'mill certificate': 'Certificate of Inspection for Organic Products',
    'Mill Test Certificate': 'Certificate of Inspection for Organic Products',
    'mill test certificate': 'Certificate of Inspection for Organic Products',
    'Material Test Certificate': 'Certificate of Inspection for Organic Products',
    'material test certificate': 'Certificate of Inspection for Organic Products',
    'Quality Certificate': 'Certificate of Inspection for Organic Products',
    'quality certificate': 'Certificate of Inspection for Organic Products',
    'Test Certificate': 'Certificate of Inspection for Organic Products',
    'test certificate': 'Certificate of Inspection for Organic Products'
}

# Special document types that are always valid
SPECIAL_DOCUMENT_TYPES = {'Empty/Insufficient Text', 'Unknown'}


@dataclass
class ValidationResult:
    """
    Data class representing the result of document validation.
    
    Attributes:
        validated_classifications: List of validated page classifications
        validation_warnings: List of warning messages for invalid types
        valid_count: Number of valid document types found
        mapped_count: Number of document types that were mapped from aliases
        invalid_count: Number of invalid document types found
        duplicate_count: Number of duplicate document types filtered
        processing_time: Time taken for validation in seconds
    """
    validated_classifications: List[Dict[str, Any]] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    valid_count: int = 0
    mapped_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'validated_classifications': self.validated_classifications,
            'validation_warnings': self.validation_warnings,
            'valid_count': self.valid_count,
            'mapped_count': self.mapped_count,
            'invalid_count': self.invalid_count,
            'duplicate_count': self.duplicate_count,
            'processing_time': self.processing_time
        }


def get_document_type_aliases() -> Dict[str, str]:
    """
    Get the document type aliases mapping.
    
    Returns:
        Dict mapping alternate names to standard document types
    """
    return DOCUMENT_TYPE_ALIASES.copy()


def get_valid_document_types(entity_mappings: Dict[str, Any]) -> Set[str]:
    """
    Get the set of valid document types from entity mappings.
    
    Args:
        entity_mappings: Dictionary of entity mappings from document classifier
        
    Returns:
        Set of valid document type names
    """
    valid_types = set()
    
    for doc_id, mapping in entity_mappings.items():
        document_name = mapping.get('documentName', doc_id)
        valid_types.add(document_name)
    
    # Add special types that are always valid
    valid_types.update(SPECIAL_DOCUMENT_TYPES)
    
    return valid_types


def validate_document_types(
    page_classifications: List[Dict[str, Any]],
    valid_document_types: Set[str],
    document_type_aliases: Optional[Dict[str, str]] = None
) -> Tuple[List[Dict[str, Any]], List[str], int, int, int]:
    """
    Validate document types against predefined list and apply alias mappings.
    
    Step 4.1: Validates each page classification against the list of valid
    document types. Invalid types are mapped using aliases if available,
    otherwise marked as unknown with the AI suggestion preserved.
    
    Args:
        page_classifications: List of page classification dictionaries
        valid_document_types: Set of valid document type names
        document_type_aliases: Optional custom alias mapping (uses default if None)
        
    Returns:
        Tuple containing:
            - validated_classifications: List of validated page classifications
            - validation_warnings: List of warning messages
            - valid_count: Number of valid types
            - mapped_count: Number of mapped types
            - invalid_count: Number of invalid types
    """
    logger.info("=" * 60)
    logger.info("🔍 STEP 4.1: DOCUMENT TYPE VALIDATION")
    logger.info("=" * 60)
    
    if document_type_aliases is None:
        document_type_aliases = DOCUMENT_TYPE_ALIASES
    
    logger.info(f"📋 Valid document types count: {len(valid_document_types)}")
    logger.info(f"🔄 Document type aliases configured: {len(document_type_aliases)}")
    
    validated_classifications = []
    validation_warnings = []
    valid_count = 0
    mapped_count = 0
    invalid_count = 0
    
    for page_class in page_classifications:
        original_doc_type = page_class['document_type']
        page_num = page_class['page']
        confidence = page_class['confidence']
        
        # First check if it's a direct match with valid types
        if original_doc_type in valid_document_types:
            # Valid document type - keep as is
            validated_classifications.append(page_class)
            valid_count += 1
            logger.info(f"✅ Page {page_num}: {original_doc_type} (VALID)")
            
        # Check if it's an alias that maps to a valid type
        elif original_doc_type in document_type_aliases:
            mapped_type = document_type_aliases[original_doc_type]
            logger.info(f"🔄 Page {page_num}: '{original_doc_type}' mapped to '{mapped_type}'")
            
            # Create new classification with mapped type
            mapped_page_class = page_class.copy()
            mapped_page_class['document_type'] = mapped_type
            mapped_page_class['original_ai_type'] = original_doc_type
            mapped_page_class['was_mapped'] = True
            validated_classifications.append(mapped_page_class)
            mapped_count += 1
            logger.info(f"✅ Page {page_num}: {mapped_type} (MAPPED FROM: {original_doc_type})")
            
        else:
            # Invalid document type - mark as unknown with AI suggestion
            warning_msg = f"⚠️ Page {page_num}: '{original_doc_type}' not found in predefined document types"
            validation_warnings.append(warning_msg)
            logger.warning(warning_msg)
            
            # Create new classification with unknown type and AI suggestion
            validated_page_class = page_class.copy()
            validated_page_class['document_type'] = f"Unknown Classification Type (Not found in the list of documents provided, Suggested By AI: {original_doc_type})"
            validated_page_class['original_ai_suggestion'] = original_doc_type
            validated_page_class['validation_status'] = 'invalid'
            validated_page_class['confidence'] = max(confidence * 0.5, 10)  # Reduce confidence for invalid types
            validated_classifications.append(validated_page_class)
            invalid_count += 1
            logger.info(f"🚫 Page {page_num}: Changed to Unknown Classification Type (AI suggested: {original_doc_type})")
    
    # Log validation summary
    if validation_warnings:
        logger.warning(f"📊 Validation Summary: {len(validation_warnings)} invalid document types detected")
        for warning in validation_warnings[:3]:  # Log first 3 warnings
            logger.warning(f"   {warning}")
        if len(validation_warnings) > 3:
            logger.warning(f"   ... and {len(validation_warnings) - 3} more")
    else:
        logger.info(f"✅ All document types validated successfully")
    
    logger.info(f"📊 Validation Complete: {valid_count} valid, {mapped_count} mapped, {invalid_count} invalid")
    
    return validated_classifications, validation_warnings, valid_count, mapped_count, invalid_count


def filter_duplicate_documents(
    page_classifications: List[Dict[str, Any]],
    high_confidence_threshold: float = 99.0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Filter duplicate document types from classifications.
    
    Step 4.2: Prevents duplicate document types from appearing multiple times.
    Only allows duplicates if confidence is extremely high (99%+).
    Duplicates are converted to continuation pages.
    
    Args:
        page_classifications: List of page classification dictionaries
        high_confidence_threshold: Confidence threshold to allow duplicates (default 99.0)
        
    Returns:
        Tuple containing:
            - filtered_classifications: List of filtered page classifications
            - duplicate_count: Number of duplicates that were filtered
    """
    logger.info("=" * 60)
    logger.info("🚫 STEP 4.2: DUPLICATE DOCUMENT TYPE PREVENTION")
    logger.info("=" * 60)
    
    # Track already seen document types
    seen_document_types: Dict[str, Dict[str, Any]] = {}
    filtered_classifications = []
    duplicate_count = 0
    
    for page_class in page_classifications:
        doc_type = page_class['document_type']
        confidence = page_class['confidence']
        page_num = page_class['page']
        
        # Skip empty/insufficient text, unknown types, and unknown classification types
        if (doc_type in SPECIAL_DOCUMENT_TYPES or 
            doc_type.startswith('Unknown Classification Type')):
            filtered_classifications.append(page_class)
            continue
        
        # Check if we've seen this document type before
        if doc_type in seen_document_types:
            previous_page = seen_document_types[doc_type]['page']
            previous_confidence = seen_document_types[doc_type]['confidence']
            
            # Only allow duplicate if confidence is extremely high
            if confidence >= high_confidence_threshold:
                logger.info(f"⚠️ DUPLICATE ALLOWED: {doc_type} on page {page_num} (confidence: {confidence:.1f}% >= {high_confidence_threshold}%)")
                filtered_classifications.append(page_class)
                # Update to track the highest confidence occurrence
                if confidence > previous_confidence:
                    seen_document_types[doc_type] = {'page': page_num, 'confidence': confidence}
            else:
                logger.info(f"🚫 DUPLICATE BLOCKED: {doc_type} on page {page_num} (confidence: {confidence:.1f}% < {high_confidence_threshold}%). Already seen on page {previous_page}")
                # Convert to continuation page
                page_class_copy = page_class.copy()
                page_class_copy['document_type'] = f"{doc_type}_Continuation"
                page_class_copy['is_duplicate_filtered'] = True
                page_class_copy['original_type'] = doc_type
                filtered_classifications.append(page_class_copy)
                duplicate_count += 1
        else:
            # First occurrence of this document type
            seen_document_types[doc_type] = {'page': page_num, 'confidence': confidence}
            filtered_classifications.append(page_class)
            logger.info(f"✅ NEW TYPE: {doc_type} on page {page_num} (confidence: {confidence:.1f}%)")
    
    logger.info(f"📊 Duplicate filtering complete. {duplicate_count} duplicates filtered")
    
    return filtered_classifications, duplicate_count


class DocumentValidationService:
    """
    Service class for document type validation.
    
    Provides a unified interface for:
    - Step 4.1: Validating document types against predefined list
    - Step 4.2: Filtering duplicate document types
    
    Usage:
        service = DocumentValidationService(entity_mappings)
        result = service.validate(page_classifications)
    """
    
    def __init__(self, entity_mappings: Optional[Dict[str, Any]] = None):
        """
        Initialize the validation service.
        
        Args:
            entity_mappings: Dictionary of entity mappings from document classifier
        """
        logger.info("DocumentValidationService initialized")
        
        self.entity_mappings = entity_mappings or {}
        self.valid_document_types = get_valid_document_types(self.entity_mappings)
        self.document_type_aliases = get_document_type_aliases()
        
        logger.info(f"📋 Loaded {len(self.valid_document_types)} valid document types")
        logger.info(f"🔄 Loaded {len(self.document_type_aliases)} document type aliases")
    
    def validate(
        self,
        page_classifications: List[Dict[str, Any]],
        filter_duplicates: bool = True,
        high_confidence_threshold: float = 99.0
    ) -> ValidationResult:
        """
        Validate page classifications and optionally filter duplicates.
        
        Args:
            page_classifications: List of page classification dictionaries
            filter_duplicates: Whether to filter duplicate document types
            high_confidence_threshold: Confidence threshold for duplicate filtering
            
        Returns:
            ValidationResult with validated classifications and statistics
        """
        import time
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("🏷️ DOCUMENT VALIDATION SERVICE")
        logger.info("=" * 60)
        logger.info(f"📄 Pages to validate: {len(page_classifications)}")
        
        result = ValidationResult()
        
        # Step 4.1: Validate document types
        validated_classifications, warnings, valid_count, mapped_count, invalid_count = \
            validate_document_types(
                page_classifications,
                self.valid_document_types,
                self.document_type_aliases
            )
        
        result.validation_warnings = warnings
        result.valid_count = valid_count
        result.mapped_count = mapped_count
        result.invalid_count = invalid_count
        
        # Step 4.2: Filter duplicates (optional)
        if filter_duplicates:
            validated_classifications, duplicate_count = filter_duplicate_documents(
                validated_classifications,
                high_confidence_threshold
            )
            result.duplicate_count = duplicate_count
        
        result.validated_classifications = validated_classifications
        result.processing_time = time.time() - start_time
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ VALIDATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"   Valid: {result.valid_count}")
        logger.info(f"   Mapped: {result.mapped_count}")
        logger.info(f"   Invalid: {result.invalid_count}")
        logger.info(f"   Duplicates filtered: {result.duplicate_count}")
        logger.info(f"   Processing time: {result.processing_time:.2f}s")
        
        return result
    
    def add_alias(self, alias: str, standard_type: str) -> None:
        """
        Add a new document type alias.
        
        Args:
            alias: The alternate name to map from
            standard_type: The standard document type name to map to
        """
        self.document_type_aliases[alias] = standard_type
        logger.info(f"➕ Added alias: '{alias}' -> '{standard_type}'")
    
    def add_valid_type(self, document_type: str) -> None:
        """
        Add a new valid document type.
        
        Args:
            document_type: The document type name to add
        """
        self.valid_document_types.add(document_type)
        logger.info(f"➕ Added valid type: '{document_type}'")
    
    def is_valid_type(self, document_type: str) -> bool:
        """
        Check if a document type is valid.
        
        Args:
            document_type: The document type name to check
            
        Returns:
            True if the type is valid, False otherwise
        """
        return document_type in self.valid_document_types
    
    def get_mapped_type(self, document_type: str) -> Optional[str]:
        """
        Get the standard type for an alias.
        
        Args:
            document_type: The document type name to check
            
        Returns:
            The standard type if an alias exists, None otherwise
        """
        return self.document_type_aliases.get(document_type)
