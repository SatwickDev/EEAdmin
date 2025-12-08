"""
SWIFT Routes Module
===================

Flask routes for SWIFT message generation and parsing operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from flask import Blueprint, request, jsonify, render_template, session
from bson import ObjectId

from .mt700_generator import generate_mt700_message, validate_lc_data_for_mt700
from .parsers import parse_swift_message_text, parse_swift_message_for_ui

logger = logging.getLogger(__name__)

# Create Blueprint for SWIFT routes
swift_bp = Blueprint('swift', __name__)

# Module-level database reference
_db = None


def init_swift_routes(db):
    """
    Initialize SWIFT routes with database connection.
    
    Args:
        db: MongoDB database instance
    """
    global _db
    _db = db
    logger.info("✅ SWIFT routes initialized with database connection")


def register_swift_routes(app, db=None):
    """
    Register SWIFT routes with Flask application.
    
    This function registers all SWIFT-related routes with the Flask app.
    Routes are available under /api/lc/ and /api/compliance/ prefixes.
    
    Args:
        app: Flask application instance
        db: MongoDB database instance (optional, can be set later via init)
    """
    global _db
    if db is not None:
        _db = db
    
    # Register the blueprint
    # Note: Routes are defined within register_routes to access app context
    _register_routes_internal(app)
    
    logger.info("✅ SWIFT Processing routes registered successfully")


def _register_routes_internal(app):
    """Internal function to register routes within app context."""
    
    @app.route('/api/lc/swift-preview-form', methods=['POST'])
    def generate_swift_preview_from_form():
        """
        Generate SWIFT MT700 preview from form data without saving to database.
        
        Request JSON:
            - lcNumber: Documentary credit number
            - applicant: Applicant name
            - beneficiary: Beneficiary name
            - amount: Credit amount
            - currency: Currency code
            - ... (other LC fields)
            
        Returns:
            JSON with success status and generated SWIFT message
        """
        logger.info("📨 SWIFT_Processing: Generating SWIFT preview from form data")
        try:
            form_data = request.get_json()

            # Validate required fields
            required_fields = ['lcNumber', 'applicant', 'beneficiary', 'amount', 'currency']
            missing_fields = [field for field in required_fields if not form_data.get(field)]

            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400

            # Generate SWIFT MT700 message from form data
            swift_message = generate_mt700_message(form_data)

            return jsonify({
                'success': True,
                'message': 'SWIFT MT700 preview generated successfully',
                'swift_message': swift_message,
                'lcNumber': form_data.get('lcNumber'),
                'preview': True
            })

        except Exception as e:
            logger.error(f"Error generating SWIFT preview: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error generating SWIFT preview: {str(e)}'
            }), 500

    @app.route('/api/lc/swift-message', methods=['GET', 'POST'])
    def get_or_generate_swift():
        """
        Get existing SWIFT message or generate if not exists.
        
        GET:
            Query params: lcNumber
            Returns: Existing or newly generated SWIFT message
            
        POST:
            Request JSON: lcNumber
            Returns: Generated SWIFT message
        """
        logger.info(f"📨 SWIFT_Processing: Get/Generate SWIFT message ({request.method})")
        try:
            if _db is None:
                return jsonify({
                    'success': False,
                    'message': 'Database not initialized'
                }), 500

            if request.method == 'GET':
                # GET request - retrieve SWIFT message
                lc_number = request.args.get('lcNumber')
                if not lc_number:
                    return jsonify({
                        'success': False,
                        'message': 'LC Number is required'
                    }), 400

                lc_collection = _db.letter_of_credits
                lc_data = lc_collection.find_one({'lcNumber': lc_number})
                
                if not lc_data:
                    return jsonify({
                        'success': False,
                        'message': 'LC not found'
                    }), 404

                # Generate SWIFT message from LC data
                swift_message = generate_mt700_message(lc_data)
                
                return jsonify({
                    'success': True,
                    'swiftMessage': swift_message,
                    'lcNumber': lc_number
                }), 200
            
            else:
                # POST request - generate and store SWIFT message
                data = request.get_json()
                lc_number = data.get('lcNumber')
                
                if not lc_number:
                    return jsonify({
                        'success': False,
                        'message': 'LC Number is required'
                    }), 400

                lc_collection = _db.letter_of_credits
                lc_data = lc_collection.find_one({'lcNumber': lc_number})
                
                if not lc_data:
                    return jsonify({
                        'success': False,
                        'message': 'LC not found'
                    }), 404

                # Generate SWIFT message
                swift_message = generate_mt700_message(lc_data)
                
                return jsonify({
                    'success': True,
                    'swiftMessage': swift_message,
                    'lcNumber': lc_number
                }), 200
                
        except Exception as e:
            logger.error(f"Error getting/generating SWIFT message: {e}")
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}'
            }), 500

    @app.route('/api/lc/generate-swift', methods=['POST'])
    def generate_swift_mt700():
        """
        Generate SWIFT MT700 message from LC data and store in database.
        
        Request JSON:
            - lcId: LC document ID (optional)
            - lcNumber: LC number (optional, used if lcId not provided)
            
        Returns:
            JSON with success status, SWIFT message, and stored message ID
        """
        logger.info("📨 SWIFT_Processing: Generating MT700 message")
        try:
            if _db is None:
                return jsonify({
                    'success': False,
                    'message': 'Database not initialized'
                }), 500

            data = request.get_json()
            lc_id = data.get('lcId')
            lc_number = data.get('lcNumber')

            # Get LC data from database
            lc_collection = _db.letter_of_credits

            if lc_id:
                lc_data = lc_collection.find_one({'_id': ObjectId(lc_id)})
            elif lc_number:
                lc_data = lc_collection.find_one({'lcNumber': lc_number})
            else:
                return jsonify({
                    'success': False,
                    'message': 'LC ID or LC Number is required'
                }), 400

            if not lc_data:
                return jsonify({
                    'success': False,
                    'message': 'LC not found'
                }), 404

            # Generate SWIFT MT700 message
            swift_message = generate_mt700_message(lc_data)

            # Store SWIFT message in database
            swift_collection = _db.swift_messages
            swift_document = {
                'lcId': str(lc_data['_id']),
                'lcNumber': lc_data['lcNumber'],
                'messageType': 'MT700',
                'swiftMessage': swift_message,
                'status': 'generated',
                'createdAt': datetime.utcnow()
            }

            swift_result = swift_collection.insert_one(swift_document)

            return jsonify({
                'success': True,
                'message': 'SWIFT MT700 message generated successfully',
                'swiftMessage': swift_message,
                'swiftId': str(swift_result.inserted_id)
            }), 200

        except Exception as e:
            logger.error(f"Error generating SWIFT MT700: {e}")
            return jsonify({
                'success': False,
                'message': 'Error generating SWIFT message'
            }), 500

    @app.route('/api/lc/swift-preview/<lc_id>')
    def preview_swift_mt700(lc_id):
        """
        Preview SWIFT MT700 message for an LC without saving.
        
        Args:
            lc_id: LC document ID
            
        Returns:
            JSON with success status and SWIFT message preview
        """
        logger.info(f"📨 SWIFT_Processing: Preview MT700 for LC ID: {lc_id}")
        try:
            if _db is None:
                return jsonify({
                    'success': False,
                    'message': 'Database not initialized'
                }), 500

            lc_collection = _db.letter_of_credits
            lc_data = lc_collection.find_one({'_id': ObjectId(lc_id)})

            if not lc_data:
                return jsonify({
                    'success': False,
                    'message': 'LC not found'
                }), 404

            # Generate SWIFT MT700 message preview (without saving)
            swift_message = generate_mt700_message(lc_data)

            return jsonify({
                'success': True,
                'swiftMessage': swift_message,
                'lcNumber': lc_data['lcNumber']
            }), 200

        except Exception as e:
            logger.error(f"Error previewing SWIFT MT700: {e}")
            return jsonify({
                'success': False,
                'message': 'Error generating SWIFT preview'
            }), 500

    @app.route('/api/compliance/swift/parse', methods=['POST'])
    def parse_swift_message():
        """
        Parse SWIFT message from text input.
        
        Request JSON:
            - swift_text: Raw SWIFT message text
            
        Returns:
            JSON with parsed SWIFT message data
        """
        logger.info("📨 SWIFT_Processing: Parsing SWIFT message")
        try:
            data = request.get_json()
            swift_text = data.get('swift_text', '')

            if not swift_text:
                return jsonify({
                    'success': False,
                    'error': 'SWIFT message text is required'
                }), 400

            # Parse SWIFT message
            parsed_swift = parse_swift_message_text(swift_text)

            return jsonify({
                'success': True,
                'parsed_swift': parsed_swift
            })

        except Exception as e:
            logger.error(f"Error parsing SWIFT message: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/swift/validate', methods=['POST'])
    def validate_swift_data():
        """
        Validate LC data for MT700 generation.
        
        Request JSON:
            LC data fields
            
        Returns:
            JSON with validation result
        """
        logger.info("📨 SWIFT_Processing: Validating SWIFT data")
        try:
            lc_data = request.get_json()
            
            validation_result = validate_lc_data_for_mt700(lc_data)
            
            return jsonify({
                'success': True,
                'validation': validation_result
            })
            
        except Exception as e:
            logger.error(f"Error validating SWIFT data: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/swift/messages', methods=['GET'])
    def get_swift_messages():
        """
        Get all SWIFT messages for an LC.
        
        Query params:
            - lcNumber: LC number to filter by
            
        Returns:
            JSON with list of SWIFT messages
        """
        logger.info(f"📨 SWIFT_Processing: Getting SWIFT messages for LC: {request.args.get('lcNumber')}")
        try:
            if _db is None:
                return jsonify({
                    'success': False,
                    'message': 'Database not initialized'
                }), 500

            lc_number = request.args.get('lcNumber')
            
            if not lc_number:
                return jsonify({
                    'success': False,
                    'message': 'LC Number is required'
                }), 400
            
            swift_collection = _db.swift_messages
            messages = list(swift_collection.find(
                {'lcNumber': lc_number},
                {'_id': 1, 'messageType': 1, 'status': 1, 'createdAt': 1}
            ).sort('createdAt', -1))
            
            # Convert ObjectId to string
            for msg in messages:
                msg['_id'] = str(msg['_id'])
            
            return jsonify({
                'success': True,
                'messages': messages,
                'count': len(messages)
            })
            
        except Exception as e:
            logger.error(f"Error getting SWIFT messages: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ==================== LC Form Pages (MT700 Template) ====================

    @app.route('/trade_finance_lc_form', methods=['GET', 'POST'])
    def trade_finance_lc_form():
        """
        Render the Trade Finance LC form with MT700 template loading and form handling.
        
        GET:
            - Renders the LC form page
            - Supports ?template=sample or ?load_template=true for sample data
            - Returns JSON if load_template=true (AJAX request)
            
        POST:
            - Handles form submission
            - Stores LC data in database
            - Returns success response with LC number and transaction ID
        """
        logger.info(f"📋 SWIFT_Processing: Trade Finance LC Form ({request.method})")
        
        if request.method == 'POST':
            # Handle form submission
            try:
                if _db is None:
                    return jsonify({
                        'success': False,
                        'message': 'Database not initialized'
                    }), 500

                # Get form data
                form_data = request.form.to_dict()
                form_data['user_id'] = session.get('user_id', 'anonymous')
                form_data['timestamp'] = datetime.utcnow()
                form_data['status'] = 'submitted'

                # Generate LC number if not provided
                if not form_data.get('lcNumber'):
                    form_data['lcNumber'] = f"LC{datetime.now().strftime('%Y%m%d%H%M%S')}"

                # Store in database
                result = _db.lc_transactions.insert_one(form_data)

                # Return success response
                return jsonify({
                    'success': True,
                    'message': 'LC form submitted successfully!',
                    'lcNumber': form_data['lcNumber'],
                    'transactionId': str(result.inserted_id),
                    'showSwiftPreview': True
                })
            except Exception as e:
                logger.error(f"Error submitting LC form: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': f'Error submitting form: {str(e)}'
                }), 500

        else:
            # Handle GET request - render form with optional template data
            template_data = {}

            # Check if loading a sample template (handle both template=sample and load_template=true)
            load_template = request.args.get('template', '')
            load_template_flag = request.args.get('load_template', '').lower() == 'true'

            if load_template == 'sample' or load_template_flag:
                template_data = {
                    'lcNumber': 'LC' + datetime.now().strftime('%Y%m%d%H%M%S'),
                    'lcType': 'irrevocable',
                    'issueDate': datetime.now().strftime('%Y-%m-%d'),
                    'expiryDate': (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d'),
                    'applicant': 'ABC Trading Company\n123 Business Street\nNew York, NY 10001\nUSA',
                    'beneficiary': 'XYZ Export Limited\n456 Export Avenue\nLondon, EC1A 1BB\nUnited Kingdom',
                    'issuingBank': 'International Trade Bank\nSWIFT: ITBKUS33\n789 Banking Plaza\nNew York, NY 10005',
                    'advisingBank': 'Global Commerce Bank\nSWIFT: GCBKGB2L\n321 Financial District\nLondon, EC2V 8RF',
                    'currency': 'USD',
                    'amount': '500000.00',
                    'tolerancePercent': '5',
                    'paymentTerms': 'sight',
                    'placeOfTaking': 'New York Port',
                    'portOfLoading': 'New York, NY',
                    'portOfDischarge': 'London, UK',
                    'finalDestination': 'London, United Kingdom',
                    'latestShipmentDate': (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'),
                    'partialShipment': 'allowed',
                    'transhipment': 'not_allowed',
                    'incoterms': 'CIF',
                    'goodsDescription': 'High-quality electronic components including:\n- Microprocessors (1000 units)\n- Memory modules (2000 units)\n- Circuit boards (500 units)\nAll items conform to international standards.',
                    'hsCode': '8542.31.0000',
                    'quantity': '3500 units',
                    'additionalDocuments': 'Commercial Invoice in triplicate\nPacking List\nCertificate of Origin\nInsurance Certificate',
                    'additionalConditions': 'All documents must be presented within 21 days of shipment date.\nInsurance to be effected for 110% of invoice value.',
                    'charges': 'applicant',
                    'repository_id': request.args.get('repository_id', 'import_lc'),
                    'documents': ['commercial_invoice', 'packing_list', 'bill_of_lading', 'certificate_of_origin']
                }

                # If load_template=true, return JSON response for AJAX
                if load_template_flag:
                    return jsonify({
                        'success': True,
                        'template': template_data
                    })
            else:
                # Load form data from GET parameters if provided
                for key in request.args:
                    if key not in ['template', 'load_template']:
                        template_data[key] = request.args.get(key)

            return render_template('trade_finance_lc_form.html', **template_data)

    # ==================== LC Data Management Routes ====================

    @app.route('/api/lc/retrieve', methods=['POST'])
    def retrieve_lc_data():
        """Retrieve LC data by LC number from database"""
        logger.info("📋 SWIFT_Processing: Retrieve LC data")
        try:
            if _db is None:
                return jsonify({
                    'success': False,
                    'message': 'Database not initialized'
                }), 500

            data = request.get_json()
            lc_number = data.get('lcNumber', '').strip()
            
            if not lc_number:
                return jsonify({
                    'success': False,
                    'message': 'LC Number is required'
                }), 400
            
            # Query database for LC with this LC number
            lc_record = _db.letter_of_credits.find_one({'lcNumber': lc_number})
            lc_records = _db.letter_of_credits.find()
            logger.info(f"all lcs present in the db :")
            for idx, record in enumerate(lc_records, start=1):
                logger.info(f"lc {idx} present in the db: {record}")

            logger.info(f"lc data requested:{lc_record}")
            if not lc_record:
                return jsonify({
                    'success': False,
                    'message': f'LC Number {lc_number} not found in the system'
                }), 404
            
            # Remove MongoDB ObjectId from response (convert to string)
            lc_record['_id'] = str(lc_record['_id'])
            
            # Convert datetime objects to ISO format strings
            if 'timestamp' in lc_record and isinstance(lc_record['timestamp'], datetime):
                lc_record['timestamp'] = lc_record['timestamp'].isoformat()
            
            return jsonify({
                'success': True,
                'message': 'LC data retrieved successfully',
                'data': lc_record
            }), 200
            
        except Exception as e:
            logger.error(f"Error retrieving LC data: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error retrieving LC data: {str(e)}'
            }), 500

    @app.route('/api/lc/list', methods=['GET'])
    def get_all_lcs():
        """Fetch all available LCs from database, sorted by latest first"""
        logger.info("📋 SWIFT_Processing: List all LCs")
        try:
            if _db is None:
                return jsonify({
                    'success': False,
                    'message': 'Database not initialized'
                }), 500

            # Query all LCs and sort by timestamp descending (latest first)
            lcs = list(_db.letter_of_credits.find({}).sort('timestamp', -1))
            
            # Convert ObjectId to string and handle datetime objects for JSON serialization
            for lc in lcs:
                lc['_id'] = str(lc['_id'])
                if 'timestamp' in lc and isinstance(lc['timestamp'], datetime):
                    lc['timestamp'] = lc['timestamp'].isoformat()
            
            logger.info(f"Retrieved {len(lcs)} LCs from database")
            
            return jsonify({
                'success': True,
                'data': lcs
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching LC list: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error fetching LCs: {str(e)}'
            }), 500

    @app.route('/api/lc/submit', methods=['POST'])
    def submit_lc_form():
        """Submit Letter of Credit form and store in database"""
        logger.info("📋 SWIFT_Processing: Submit LC form")
        try:
            if _db is None:
                return jsonify({
                    'success': False,
                    'message': 'Database not initialized'
                }), 500

            data = request.get_json()

            # Validate required fields
            required_fields = ['lcNumber', 'lcType', 'issueDate', 'expiryDate', 'applicant',
                               'beneficiary', 'issuingBank', 'currency', 'amount', 'paymentTerms',
                               'latestShipmentDate', 'goodsDescription']

            missing_fields = []
            for field in required_fields:
                if not data.get(field):
                    missing_fields.append(field)

            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400

            # Validate dates
            try:
                issue_date = datetime.strptime(data['issueDate'], '%Y-%m-%d')
                expiry_date = datetime.strptime(data['expiryDate'], '%Y-%m-%d')
                shipment_date = datetime.strptime(data['latestShipmentDate'], '%Y-%m-%d')

                if expiry_date <= issue_date:
                    return jsonify({
                        'success': False,
                        'message': 'Expiry date must be after issue date'
                    }), 400

                if shipment_date >= expiry_date:
                    return jsonify({
                        'success': False,
                        'message': 'Shipment date must be before expiry date'
                    }), 400

            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400

            # Validate amount
            try:
                amount = float(data['amount'])
                if amount <= 0:
                    return jsonify({
                        'success': False,
                        'message': 'Amount must be greater than zero'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Invalid amount format'
                }), 400

            # Validate LC number uniqueness
            lc_collection = _db.letter_of_credits
            submitted_lc_number = data['lcNumber']  # Keep original for response

            # Check if LC number already exists
            existing_lc = lc_collection.find_one({'lcNumber': data['lcNumber']})
            
            # Prepare LC document with new/updated fields
            lc_document = {
                'lcNumber': data['lcNumber'],
                'lcType': data['lcType'],
                'issueDate': data['issueDate'],
                'expiryDate': data['expiryDate'],
                'applicant': data['applicant'],
                'beneficiary': data['beneficiary'],
                'issuingBank': data['issuingBank'],
                'advisingBank': data.get('advisingBank', ''),
                'currency': data['currency'],
                'amount': amount,
                'tolerancePercent': data.get('tolerancePercent', 0),
                'paymentTerms': data['paymentTerms'],
                'placeOfTaking': data.get('placeOfTaking', ''),
                'portOfLoading': data.get('portOfLoading', ''),
                'portOfDischarge': data.get('portOfDischarge', ''),
                'finalDestination': data.get('finalDestination', ''),
                'latestShipmentDate': data['latestShipmentDate'],
                'partialShipment': data.get('partialShipment', 'allowed'),
                'transhipment': data.get('transhipment', 'allowed'),
                'incoterms': data.get('incoterms', ''),
                'goodsDescription': data['goodsDescription'],
                'hsCode': data.get('hsCode', ''),
                'quantity': data.get('quantity', ''),
                'documents': data.get('documents', []),
                'documentsRequired': data.get('documentsRequired', ''),
                'additionalDocuments': data.get('additionalDocuments', ''),
                'additionalConditions': data.get('additionalConditions', ''),
                'charges': data.get('charges', 'beneficiary'),
                'status': 'submitted',
                'createdAt': existing_lc['createdAt'] if existing_lc else datetime.utcnow(),
                'updatedAt': datetime.utcnow()
            }

            # Remove empty string values to avoid overwriting with blanks
            lc_document = {k: v for k, v in lc_document.items() if v != ''}

            # Insert or update into database with smart merge logic
            result = lc_collection.update_one(
                {'lcNumber': data['lcNumber']},
                {
                    '$set': lc_document,
                },
                upsert=True
            )

            if result.upserted_id:
                # New LC was created
                transaction_id = str(result.upserted_id)
                logger.info(f"LC inserted: {data['lcNumber']} - ID: {transaction_id}")
            else:
                # LC was updated or already exists
                existing_lc = lc_collection.find_one({'lcNumber': data['lcNumber']})
                transaction_id = str(existing_lc['_id'])
                logger.info(f"LC updated: {data['lcNumber']} (modified: {result.modified_count}) - ID: {transaction_id}")
            
            logger.info(f"LC form submitted successfully: {data['lcNumber']}")

            return jsonify({
                'success': True,
                'message': 'Letter of Credit submitted successfully',
                'lcNumber': data['lcNumber'],
                'lcId': transaction_id,
                'transactionId': transaction_id,
                'redirect': f'/lc_success?lcNumber={data["lcNumber"]}&transactionId={transaction_id}'
            }), 200

        except Exception as e:
            logger.error(f"Error submitting LC form: {e}")
            return jsonify({
                'success': False,
                'message': 'Internal server error during LC submission'
            }), 500

    logger.info("✅ All SWIFT routes registered")
