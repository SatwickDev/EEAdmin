# Smart Banking Chat Database Schema

## Overview
This document describes the database schema for the Smart Banking Chat application with conversation history management, smart suggestions, and auto-fill functionality.

## Collections

### 1. conversation_history
Stores all chat messages and responses for context management.

```javascript
{
  _id: ObjectId,
  user_id: String,              // Reference to user
  session_id: String,           // Chat session identifier
  message: String,              // User's message
  response: String,             // AI's response
  message_type: String,         // "chat", "transaction", "payment", "transfer"
  timestamp: Date,              // Message timestamp
  metadata: {                   // Additional context data
    transaction_type: String,
    amount: Number,
    beneficiary_name: String,
    account_number: String,
    bank_name: String,
    purpose: String,
    confidence_score: Number,
    processing_time: Number
  },
  message_id: String           // Unique message identifier
}
```

**Indexes:**
- `{user_id: 1, timestamp: -1}` - For user conversation history
- `{session_id: 1}` - For session-based queries
- `{message_type: 1, timestamp: -1}` - For filtering by message type

### 2. templates
Stores reusable transaction templates for quick access.

```javascript
{
  _id: ObjectId,
  user_id: String,              // Owner of the template
  title: String,                // Template display name
  category: String,             // "transfer", "payment", "deposit", "general"
  data: {                       // Template data
    beneficiary_name: String,
    account_number: String,
    bank_name: String,
    swift_code: String,
    amount: Number,
    purpose: String,
    currency: String,
    transaction_type: String
  },
  keywords: [String],           // Keywords for search/matching
  usage_count: Number,          // How often template is used
  created_at: Date,
  last_used: Date,
  description: String           // Template description
}
```

**Indexes:**
- `{user_id: 1, category: 1}` - For category-based filtering
- `{user_id: 1, usage_count: -1}` - For popular templates
- `{keywords: 1}` - For keyword search

### 3. beneficiaries
Stores frequently used beneficiary information for auto-fill.

```javascript
{
  _id: ObjectId,
  user_id: String,              // Owner of the beneficiary
  name: String,                 // Beneficiary full name
  account_number: String,       // Account number
  bank_name: String,            // Bank name
  swift_code: String,           // SWIFT/BIC code
  branch_code: String,          // Branch code if applicable
  address: String,              // Beneficiary address
  country: String,              // Country code
  currency: String,             // Default currency
  frequency: Number,            // Usage frequency
  total_amount: Number,         // Total amount transferred
  last_amount: Number,          // Last transaction amount
  created_at: Date,
  last_used: Date,
  is_active: Boolean,           // Active status
  notes: String                 // Additional notes
}
```

**Indexes:**
- `{user_id: 1, name: 1}` - For name-based search
- `{user_id: 1, frequency: -1}` - For popular beneficiaries
- `{user_id: 1, last_used: -1}` - For recent beneficiaries

### 4. transaction_patterns
Stores transaction patterns for intelligent suggestions.

```javascript
{
  _id: ObjectId,
  pattern_id: String,           // Unique pattern identifier (hash)
  user_id: String,              // Pattern owner
  keywords: [String],           // Extracted keywords
  frequency: Number,            // Pattern frequency
  template_data: {              // Pattern template
    beneficiary_name: String,
    account_number: String,
    bank_name: String,
    amount_range: {
      min: Number,
      max: Number,
      avg: Number
    },
    purpose: String,
    transaction_type: String,
    day_of_week: Number,        // Common day (0-6)
    time_of_day: Number         // Common hour (0-23)
  },
  created_at: Date,
  last_used: Date,
  description: String,          // Pattern description
  confidence_score: Number      // Pattern reliability score
}
```

**Indexes:**
- `{user_id: 1, frequency: -1}` - For popular patterns
- `{pattern_id: 1}` - For pattern updates
- `{keywords: 1}` - For keyword matching

### 5. smart_suggestions
Stores AI-generated suggestions for optimization.

```javascript
{
  _id: ObjectId,
  user_id: String,              // Target user
  suggestion_type: String,      // "template", "beneficiary", "pattern", "optimization"
  title: String,                // Suggestion title
  description: String,          // Detailed description
  data: Object,                 // Suggestion data
  confidence_score: Number,     // AI confidence (0-1)
  created_at: Date,
  shown_at: Date,               // When shown to user
  applied_at: Date,             // When user applied suggestion
  dismissed_at: Date,           // When user dismissed
  status: String,               // "pending", "applied", "dismissed"
  context: {                    // Context that triggered suggestion
    input_text: String,
    transaction_type: String,
    session_id: String
  }
}
```

**Indexes:**
- `{user_id: 1, status: 1}` - For pending suggestions
- `{user_id: 1, confidence_score: -1}` - For best suggestions
- `{created_at: -1}` - For recent suggestions

### 6. auto_fill_cache
Caches frequently accessed auto-fill data for performance.

```javascript
{
  _id: ObjectId,
  user_id: String,              // Cache owner
  cache_key: String,            // Unique cache key
  cache_type: String,           // "beneficiary", "template", "pattern"
  data: Object,                 // Cached data
  access_count: Number,         // Access frequency
  created_at: Date,
  last_accessed: Date,
  expires_at: Date,             // Cache expiration
  is_valid: Boolean             // Cache validity
}
```

**Indexes:**
- `{user_id: 1, cache_key: 1}` - For cache lookup
- `{expires_at: 1}` - For cache cleanup
- `{user_id: 1, access_count: -1}` - For popular cache entries

## Enhanced Existing Collections

### users (Enhanced)
```javascript
{
  // ... existing fields ...
  preferences: {
    auto_fill_enabled: Boolean,
    smart_suggestions_enabled: Boolean,
    conversation_history_days: Number,
    template_sharing_enabled: Boolean,
    notification_preferences: {
      new_suggestions: Boolean,
      transaction_reminders: Boolean,
      pattern_alerts: Boolean
    }
  },
  usage_stats: {
    total_conversations: Number,
    total_templates: Number,
    total_beneficiaries: Number,
    avg_session_duration: Number,
    last_activity: Date
  }
}
```

### sessions (Enhanced)
```javascript
{
  // ... existing fields ...
  conversation_count: Number,
  last_suggestion_at: Date,
  session_metadata: {
    user_agent: String,
    ip_address: String,
    device_type: String,
    location: String
  }
}
```

## Data Flow

### 1. Message Processing Flow
```
User Message → Conversation History → Context Extraction → AI Processing → Smart Suggestions → Response Storage
```

### 2. Auto-fill Flow
```
User Input → Pattern Matching → Beneficiary Lookup → Template Matching → Suggestion Ranking → UI Display
```

### 3. Template Learning Flow
```
Transaction Completion → Data Extraction → Pattern Analysis → Template Creation → Keyword Extraction → Storage
```

## Performance Considerations

### 1. Indexing Strategy
- Compound indexes for common query patterns
- TTL indexes for cache cleanup
- Sparse indexes for optional fields

### 2. Data Retention
- Conversation history: 90 days default
- Templates: Keep active templates indefinitely
- Patterns: Archive after 6 months of inactivity
- Cache: 24-hour TTL for auto-fill data

### 3. Query Optimization
- Limit conversation history queries to recent sessions
- Use aggregation pipelines for complex suggestions
- Implement read-through caching for frequently accessed data

## Security Considerations

### 1. Data Encryption
- Encrypt sensitive fields (account numbers, amounts)
- Use MongoDB field-level encryption for PII
- Implement proper access controls

### 2. Data Anonymization
- Hash pattern IDs to prevent reverse engineering
- Anonymize conversation data for analytics
- Implement proper data retention policies

### 3. Access Controls
- User-based data isolation
- Session-based access validation
- Rate limiting for API endpoints

## Migration Scripts

### Initial Setup
```javascript
// Create collections with proper indexes
db.conversation_history.createIndex({"user_id": 1, "timestamp": -1});
db.templates.createIndex({"user_id": 1, "usage_count": -1});
db.beneficiaries.createIndex({"user_id": 1, "frequency": -1});
db.transaction_patterns.createIndex({"user_id": 1, "frequency": -1});
db.smart_suggestions.createIndex({"user_id": 1, "confidence_score": -1});
```

### Data Migration
```javascript
// Migrate existing conversation data
db.conversation_history.updateMany(
  {metadata: {$exists: false}},
  {$set: {metadata: {}, message_type: "chat"}}
);
```

## Monitoring and Maintenance

### 1. Performance Metrics
- Query execution times
- Index usage statistics
- Cache hit rates
- Storage growth patterns

### 2. Maintenance Tasks
- Regular index optimization
- Cache cleanup procedures
- Data archival processes
- Performance monitoring

### 3. Backup Strategy
- Daily incremental backups
- Weekly full backups
- Point-in-time recovery capability
- Cross-region replication for disaster recovery