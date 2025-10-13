import threading

# Lock for conversation safety
conversation_lock = threading.Lock()

# Conversation history for user context
conversation_history = {}
