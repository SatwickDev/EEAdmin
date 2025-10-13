"""
Initialization file for the utils package.
Exposes all utility modules and functions for use across the application.
"""

# Query utilities
from .query_utils import (
    generate_sql_query,
    execute_sql_and_format,
    validate_sql_query,
    process_user_query,
    generate_visualization_with_inference,
    trigger_proactive_alerts,
    handle_follow_up_request,
    insert_trx_file_upload,
    insert_trx_file_detail,
    insert_trx_sub_files,
    insert_faef_em_inv,
    handle_creation_transaction_request,
    generate_rag_table_or_report_request,
    extract_json_from_gpt_response,
    analyze_ucp_compliance_chromaRAG,
    analyze_swift_compliance_chromaRAG,




)

# File utilities
from .file_utils import (
    extract_text_from_file,
    save_uploaded_file,
    load_faiss_index,
    retrieve_relevant_chunks,
    extract_mandatory_fields,
    extract_text_from_pdf,
    get_embedding,
    process_pdfs_in_folder,
    retrieve_relevant_chunksRAG_for_ucp,
    retrieve_relevant_chunksRAG_for_swift,


)

# API utilities
from .api_utils import (
    parse_postman_collection,
    map_query_to_api as api_map_query_to_api,  # Avoid conflict with gpt_utils
    execute_api,
    handle_api_request
)

# Compliance utilities
from .compliance_utils import (
    check_compliance,
    sanitize_user_input,
    apply_additional_compliance_checks,
)

# GPT-based utilities
from .gpt_utils import (
    generate_llm_insights as gpt_generate_llm_insights,  # Avoid conflict with query_utils
    analyze_document_with_gpt,
    map_query_to_api as gpt_map_query_to_api,
    extract_json_from_response,
    generate_response,
    classify_document_gpt
)

# Conversation management
from .conversation import (
    conversation_lock,
    conversation_history,
)

# rag ucp600


# Application configuration
from .app_config import (
    load_dotenv,
    engine,
)
