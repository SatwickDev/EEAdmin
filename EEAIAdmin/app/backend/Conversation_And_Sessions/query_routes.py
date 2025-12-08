"""
Query Routes Module
Contains the main /query and /query/stream endpoints for processing user queries
"""

from flask import request, jsonify, session, Response, stream_with_context
from datetime import datetime
import json
import time
import uuid


def register_query_routes(app, timing_aspect, logger, db,
                          get_conversation_context,
                          active_user_repositories, active_user_modules,
                          handle_follow_up_request, train_user_manual, query_trained_manual,
                          handle_custom_rule_intent, handle_api_request,
                          handle_table_or_report_request, handle_visualization_request,
                          handle_export_report_request, process_uploaded_files,
                          handle_zip_file_upload, handle_proactive_alert, schema):
    """
    Register query processing routes
    
    Args:
        app: Flask application instance
        timing_aspect: Timing decorator for performance monitoring
        logger: Logger instance
        db: MongoDB database instance
        get_conversation_context: Function to get conversation context
        active_user_repositories: Dict of active user repositories
        active_user_modules: Dict of active user modules
        handle_follow_up_request: Function to handle follow-up requests
        train_user_manual: Function to train user manual
        query_trained_manual: Function to query trained manual
        handle_custom_rule_intent: Function to handle custom rule intent
        handle_api_request: Function to handle API requests
        handle_table_or_report_request: Function to handle table/report requests
        handle_visualization_request: Function to handle visualization requests
        handle_export_report_request: Function to handle export report requests
        process_uploaded_files: Function to process uploaded files
        handle_zip_file_upload: Function to handle zip file uploads
        handle_proactive_alert: Function to handle proactive alerts
        schema: Database schema
    """

    @app.route("/query", methods=["POST"])
    @timing_aspect
    def query():
        """Handle user queries dynamically based on intent."""
        logger.info("Received a new request at /query endpoint.")
        try:
            user_query, user_id, uploaded_file, annotations = None, None, None, None
            session_id = None
            output_format = "table"
            updated_template_details = None
            json_data = None  # Initialize json_data to avoid UnboundLocalError
            repository_context = None  # Initialize repository_context

            if request.content_type == "application/json":
                logger.info("Processing JSON request.")
                json_data = request.get_json()
                user_query = json_data.get("query", "").strip() if json_data.get("query") else ""
                user_id_from_json = json_data.get("user_id") or ""
                user_id = session.get("user_id") or (user_id_from_json.strip() if user_id_from_json else "") or None
                session_id = json_data.get("session_id", None)
                productName = (json_data.get("productname") or "").strip()
                functionName = (json_data.get("functionname") or "").strip()
                scf_value = json_data.get("SCF", False)
                if isinstance(scf_value, str):
                    scf_flag = scf_value.lower() == "true"
                else:
                    scf_flag = bool(scf_value)
            elif request.content_type.startswith("multipart/form-data"):
                logger.info("Processing file upload request.")
                user_query = (request.form.get("query") or "").strip()
                user_id_from_form = request.form.get("user_id") or ""
                user_id = session.get("user_id") or (user_id_from_form.strip() if user_id_from_form else "") or None
                session_id = request.form.get("session_id", None)
                annotations = (request.form.get("annotations") or "").strip()
                uploaded_file = request.files.getlist("file")
                scf_flag = (request.form.get("SCF") or "false").lower() == "true"
                productName = (request.form.get("productname") or "").strip()
                functionName = (request.form.get("functionname") or "").strip()
                logger.info(f"SCF Flag is {scf_flag}")
            else:
                logger.warning("Unsupported content type.")
                return jsonify(
                    {"response": "Unsupported content type. Use JSON or form-data.", "intent": "unknown"}), 400

            if uploaded_file and scf_flag:
                user_query += "extract the invoice_detail information attached file"
            elif uploaded_file and not scf_flag:
                user_query += "extract the letter_of_credit information attached file"

            # Handle guest users - provide default user_id if missing
            if not user_id:
                user_id = 'guest_user'
                logger.info("Using guest_user for unauthenticated request")

            # Additional guest mode detection from URL parameters
            guest_mode = request.args.get('guest_mode') or request.args.get('guestMode') or \
                         (json_data and json_data.get('guest_mode')) or \
                         (request.form and request.form.get('guest_mode'))

            if guest_mode == 'true' and user_id != 'guest_user':
                logger.info(f"Guest mode detected, overriding user_id {user_id} with guest_user")
                user_id = 'guest_user'

            if not user_query:
                return jsonify({"response": "Missing fields: query.", "intent": "unknown"}), 400

            logger.info(f"Processing query for user_id: {user_id}, guest_mode: {guest_mode}")

            logger.info(f"🔍 product: {productName}, function: {functionName}")

            context = get_conversation_context(user_id, session_id)
            logger.info(f"User {user_id} conversation context: {context}")
            # Don't save here - frontend will save via /api/conversation/message endpoint

            # Check for repository context from request
            if json_data is not None:
                repository_context = json_data.get("repository_context")
            elif request.content_type.startswith("multipart/form-data"):
                repository_context = request.form.get("repository_context")

            # Check if user has an active repository connection (legacy)
            active_repository = active_user_repositories.get(user_id)

            # Check if user has an active module connection (new database config based)
            active_module = active_user_modules.get(user_id)

            # Update if repository context is provided in request
            if repository_context:
                active_repository = repository_context
                active_user_repositories[user_id] = repository_context
                logger.info(f"Updated active repository from request to: {repository_context}")

            logger.info(f"Active repository for user {user_id}: {active_repository}")
            logger.info(f"Active module for user {user_id}: {active_module}")

            # ✨ NEW: Use enhanced query processing with Database Configuration
            # Priority: DB Config Recipes > Knowledge Corpus > LLM
            try:
                from app.utils.process_query_with_db_config import process_user_query_with_db_config

                response = process_user_query_with_db_config(
                    user_query,
                    user_id,
                    context,
                    active_module,
                    active_repository
                )

                # Check if response contains an error
                if response and isinstance(response, dict) and "error" in response:
                    logger.warning(f"process_user_query_with_db_config returned error: {response.get('error')}")
                    raise Exception(response.get('error', 'Query processing failed'))

            except Exception as e:
                logger.error(f"Error in process_user_query_with_db_config: {str(e)}")
                # Use repository-specific fallback responses
                try:
                    from app.utils.repository_responses import get_fallback_response
                    response = get_fallback_response(user_query, active_repository or active_module)
                    logger.info(f"Using repository-specific fallback response")
                except Exception as fallback_error:
                    logger.error(f"Error getting fallback response: {fallback_error}")
                    # Ultimate fallback
                    if active_repository:
                        response = {
                            "intent": "general",
                            "answer": f"I'm connected to the {active_repository} repository. How can I help you today?"
                        }
                    else:
                        response = {
                            "intent": "general",
                            "answer": "Hello! Please connect to a repository to get started. Click on 'No Repository' above."
                        }
                logger.info(f"Using fallback response due to API error")

            # Check if response is None or invalid
            if response is None:
                logger.error("process_user_query returned None")
                response = {
                    "intent": "error",
                    "answer": "I'm sorry, I encountered an error processing your request. Please try again.",
                    "error": "Internal processing error"
                }

            # Don't save here - frontend will save via /api/conversation/message endpoint
            # Extra safety check in case response somehow becomes None
            if response is None:
                logger.error("Response is None after validation")
                return jsonify({"response": "An error occurred processing your request.", "intent": "error"}), 500

            intent = response.get("intent", "unknown")
            logger.info(f"Determined intent: {intent}")

            if response.get("confirmation_required"):
                logger.info("Confirmation required from user.")
                return jsonify({
                    "response": response.get("answer", "Are you sure you want to apply these changes?"),
                    "intent": intent,
                    "confirmation_required": True,
                    "modified_fields": response.get("modified_fields")
                })

            if intent == "Follow-Up Request":
                logger.info("Handling Follow-Up Request.")
                follow_up_intent = response.get("follow_up_intent", "unknown")
                output_format = response.get("output_format", "table")
                valid_formats = ["table", "json", "html", "report", "Excel", "text"]
                if output_format not in valid_formats:
                    logger.warning(f"Invalid output format: {output_format}. Defaulting to 'table'.")
                    output_format = "table"
                logger.info(f"Output format set to: {output_format}")
                logger.info(f"Detected Follow-Up Intent: {follow_up_intent}")
                try:
                    refined_response = handle_follow_up_request(user_query, context, follow_up_intent, output_format)
                    return jsonify({
                        "response": refined_response,
                        "intent": "Follow-Up Request",
                        "output_format": output_format
                    })
                except Exception as e:
                    logger.error(f"Error handling follow-up request: {e}")
                    return jsonify({
                        "response": "An error occurred while processing the follow-up request.",
                        "intent": "error"
                    }), 500

            elif intent in ["Train User Manual", "User Manual Request", "User Manual"] or response.get(
                    "requires_training_handler"):
                if uploaded_file and len(uploaded_file) > 0:
                    result = train_user_manual(uploaded_file[0], user_id, user_query)
                    return jsonify({
                        "response": result["message"],
                        "intent": intent,
                        "success": result["success"]
                    }), 200 if result["success"] else 400
                elif "train" not in user_query.lower():
                    # Check if the query is actually asking about training or uploading
                    if any(word in user_query.lower() for word in ['upload', 'train', 'add manual', 'load manual']):
                        return jsonify({
                            "response": "Please upload a user manual document to train.",
                            "intent": intent,
                            "follow_up_questions": ["Would you like to upload a manual now?"]
                        }), 400

                    # Query the trained manual
                    result = query_trained_manual(user_query, user_id, context)

                    # If no documents found but query seems to be about general trade finance topics
                    if not result["success"] and any(word in user_query.lower() for word in
                                                     ['trade', 'finance', 'letter of credit', 'lc', 'bill']):
                        # Try to provide a general response instead of failing
                        return jsonify({
                            "response": "I couldn't find specific information in your uploaded manuals. Please upload relevant trade finance manuals to get detailed answers about your query.",
                            "intent": intent,
                            "follow_up_questions": [
                                "Would you like to upload a trade finance manual?",
                                "Can you rephrase your question?",
                                "What specific aspect of trade finance are you interested in?"
                            ],
                            "success": False
                        }), 400

                    return jsonify({
                        "response": result.get("response", result.get("message", "No response generated")),
                        "html": result.get("html"),
                        "intent": result.get("intent", intent),
                        "output_format": result.get("output_format"),
                        "source_files": result.get("source_files"),
                        "success": result["success"]
                    }), 200 if result["success"] else 400
                else:
                    return jsonify({
                        "response": "Please upload a user manual document to train.",
                        "intent": intent,
                        "follow_up_questions": ["Please upload the user manual document."]
                    }), 400

            elif intent == "Creation Transaction":
                # Use pure conversational handler - no forms needed
                from app.utils.conversational_transaction_handler_v2 import ConversationalTransactionHandler
                handler = ConversationalTransactionHandler(db)
                query_session_id = session.get('session_id', str(uuid.uuid4()))

                # Get active repository for the user
                active_repository = active_user_repositories.get(user_id)
                result = handler.process_creation_intent(user_query, query_session_id, user_id, context, active_repository)
                return jsonify(result)
            elif intent == "Custom Rule Request":
                result = handle_custom_rule_intent(user_query, context)
                if result.get("FollowUpQuestions"):
                    return jsonify({
                        "intent": intent,
                        "follow_up_questions": result["FollowUpQuestions"],
                        "action": result.get("Action"),
                        "response": None,
                        "result": None
                    })
                else:
                    return jsonify({
                        "intent": intent,
                        "action": result.get("Action"),
                        "response": "Operation completed.",
                        "result": result.get("Result"),
                        "follow_up_questions": []
                    })
            elif intent == "api request":
                corporate_id = response.get("corporate_id", "default_corporate_id")
                return handle_api_request(user_query, user_id, corporate_id)
            elif intent in ["Table Request", "report request", "Report Request"]:
                if intent in ["report request", "Report Request"]:
                    output_format = response.get("output_format", "table")
                return handle_table_or_report_request(intent, user_query, user_id, output_format, context)
            elif intent == "Visualization Request":
                return handle_visualization_request(intent, response, user_query, user_id)
            elif intent == "Export Report Request":
                return handle_export_report_request(intent, response, user_query, user_id, context)
            elif intent == "File Upload Request":
                if not uploaded_file or len(uploaded_file) == 0:
                    return jsonify(
                        {"response": "File is required for this request.", "intent": "File Upload Request"}
                    ), 400

                # Get document type from query or annotations for field mapping
                document_type = request.form.get('documentType', None)

                if isinstance(uploaded_file, list) and len(uploaded_file) > 1:
                    return process_uploaded_files(uploaded_file, intent, userQuery=user_query, annotations=annotations,
                                                  productName=productName, functionName=functionName,
                                                  documentType=document_type)
                uploaded_file = uploaded_file[0]
                file_type = uploaded_file.content_type
                if file_type in ["application/zip", "application/x-zip-compressed"] or uploaded_file.filename.endswith(
                        ".zip"):
                    return handle_zip_file_upload(uploaded_file, intent, userQuery=user_query, annotations=annotations,
                                                  documentType=document_type)
                else:
                    return process_uploaded_files(uploaded_file, intent, userQuery=user_query, annotations=annotations,
                                                  productName=productName, functionName=functionName,
                                                  documentType=document_type)
            # elif intent == "User Manual Request":
            #     return handle_user_manual(intent, user_query, user_id)
            elif intent == "Proactive Alert Request":
                return handle_proactive_alert(user_query, user_id, schema)
            elif intent == "Robotic Action Request":
                template_name = response.get("template_name", "")
                if not template_name:
                    return jsonify(
                        {"response": "Template name is required for Robotic Action Request.", "intent": intent}), 400
                if "confirmed" in user_query.lower():
                    updated_template_details = response.get("modified_fields")
                    return jsonify({
                        "response": f"Robotic action executed: Loaded template '{template_name}'.",
                        "intent": intent,
                        "template_name": template_name,
                        "updated_template_details": updated_template_details
                    })
                else:
                    return jsonify({
                        "response": f"Robotic action executed: Loaded template '{template_name}'.",
                        "intent": intent,
                        "template_name": template_name,
                        "follow_up_questions": [
                            f"What changes would you like to make to the '{template_name}' template? (e.g., field1=value1, field2=value2)"]
                    })
            else:
                # Ensure response is not None before calling .get()
                if response is None:
                    return jsonify({"response": "Unable to process the request.", "intent": "error"}), 500
                return jsonify({"response": response.get("answer", "Unable to process the request."), "intent": intent})

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            return jsonify({"response": "An unexpected error occurred.", "intent": "error"}), 500


    @app.route("/query/stream", methods=["POST"])
    @timing_aspect
    def query_stream():
        """ChatGPT-style streaming endpoint for voice assistant."""
        logger.info("Received streaming request at /query/stream endpoint.")

        def generate_stream():
            try:
                # Parse request data
                json_data = request.get_json()
                user_query = json_data.get("query", "").strip()
                user_id = json_data.get("user_id") or session.get("user_id") or 'guest_user'
                stream_session_id = json_data.get("session_id", None)
                repository_context = json_data.get("repository_context")

                if not user_query:
                    yield f"data: {json.dumps({'error': 'Missing query field'})}\n\n"
                    return

                logger.info(f"Streaming query for user {user_id}: {user_query}")

                # Get conversation context
                context = get_conversation_context(user_id, stream_session_id)

                # Get active repository/module
                active_repository = active_user_repositories.get(user_id)
                active_module = active_user_modules.get(user_id)

                if repository_context:
                    active_repository = repository_context
                    active_user_repositories[user_id] = repository_context

                # Process query using existing infrastructure
                from app.utils.process_query_with_db_config import process_user_query_with_db_config

                response = process_user_query_with_db_config(
                    user_query,
                    user_id,
                    context,
                    session_id=stream_session_id,
                    uploaded_file=None,
                    scf_flag=False,
                    repository=active_repository,
                    active_module=active_module
                )

                intent = response.get("intent", "general")
                answer = response.get("answer", "I couldn't process that request.")

                # Stream the response word by word for realistic effect
                words = answer.split()
                for i, word in enumerate(words):
                    chunk_data = {
                        "chunk": word + " ",
                        "done": False,
                        "intent": intent
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                    # Variable delay for natural speech rhythm
                    if word.endswith(('.', '!', '?')):
                        time.sleep(0.15)  # Pause after sentences
                    elif word.endswith(','):
                        time.sleep(0.08)  # Pause after commas
                    else:
                        time.sleep(0.05)  # Normal word spacing

                # Send completion signal
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'intent': intent, 'full_response': answer})}\n\n"

            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

        return Response(
            stream_with_context(generate_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    logger.info("Query routes registered successfully")
