# Query Handler - Complete Feature Set

## ✅ **All Required Features Implemented**

---

## 1️⃣ **Vector Search Functionality** ✅

### **Implementation:**
```python
def generate_embedding(text):
    """Generate 1536-dimension vector using Amazon Titan"""
    response = bedrock_runtime.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        body=json.dumps({"inputText": text})
    )
```

### **Features:**
- ✅ Amazon Titan Embeddings integration
- ✅ 1536-dimension vectors
- ✅ OpenSearch KNN similarity search
- ✅ Cosine similarity scoring
- ✅ Top-K retrieval (configurable)

---

## 2️⃣ **Hybrid Search (Vector + Keyword)** ✅

### **Implementation:**
```python
def retrieve_relevant_chunks(query, max_results=5, use_hybrid=True):
    # Combines:
    # 1. Vector similarity (70% weight)
    # 2. Keyword matching (30% weight)
```

### **Features:**
- ✅ Vector search for semantic similarity
- ✅ Keyword search (BM25) for exact matches
- ✅ Weighted combination (70/30 split)
- ✅ Multi-field search (text + metadata)
- ✅ Fallback to pure vector if hybrid fails

### **Benefits:**
- Better results for exact term matches
- Improved recall for semantic queries
- Handles synonyms and related concepts (vector)
- Catches specific keywords (BM25)

---

## 3️⃣ **Context Optimization Logic** ✅

### **A. Dynamic Model Selection**

```python
def select_model_tier(query, conversation_history):
    # Returns: "simple", "standard", or "advanced"
```

**Selection Logic:**
| Condition | Model Tier | Model | Use Case |
|-----------|------------|-------|----------|
| Simple query, no context | Simple | Claude Instant | "What is AWS?" |
| Moderate complexity | Standard | Claude 2.1 | "Explain Lambda" |
| Complex + Technical | Advanced | Claude 3 Sonnet | "Compare architectures" |

### **B. Chunk Re-ranking**

```python
def rerank_chunks(query, chunks):
    # Adjusts scores based on:
    - Chunk length
    - Keyword overlap
    - Original relevance score
```

### **C. Token Counting & Cost Tracking**

```python
cost = calculate_cost(prompt_tokens, response_tokens, model_config)
```

---

## 4️⃣ **Dynamic Prompt Construction** ✅

### **Features:**

**Adaptive Context:**
- Includes 0-5 relevant chunks based on retrieval
- Shows relevance scores
- Handles missing context gracefully

**Conversation-Aware:**
- Includes last 3 exchanges (6 messages)
- Maintains conversation flow

**Structured Format:**
```
System Instructions
↓
Context (Relevant Chunks with scores)
↓
Previous Conversation (if exists)
↓
Current Query
```

---

## 5️⃣ **Foundation Models via Bedrock** ✅

### **Model Configuration:**

```python
models = {
    "simple": {
        "id": "anthropic.claude-instant-v1",
        "max_tokens": 500,
        "cost_per_1k_input": $0.00080
    },
    "standard": {
        "id": "anthropic.claude-v2:1",
        "max_tokens": 1000,
        "cost_per_1k_input": $0.00800
    },
    "advanced": {
        "id": "anthropic.claude-3-sonnet",
        "max_tokens": 2000,
        "cost_per_1k_input": $0.01500
    }
}
```

### **Features:**
- ✅ 3 Claude models via Bedrock
- ✅ Amazon Titan for embeddings
- ✅ Dynamic model selection
- ✅ Per-model cost tracking
- ✅ Configurable parameters (temp, max_tokens)
- ✅ Error handling & fallbacks

---

## 🎁 **Bonus Features Included**

### **1. PII Detection**
```python
def detect_pii(text):
    # AWS Comprehend integration
    # Detects: Names, emails, SSN, credit cards, etc.
```

### **2. Comprehensive Monitoring**
```python
def log_metrics(request_id, model_id, tokens, latency, cost):
    # CloudWatch metrics:
    - QueryLatency
    - PromptTokens
    - ResponseTokens  
    - QueryCost
```

### **3. Evaluation Data Storage**
```python
# Stores for later analysis:
- Query & response
- Model used
- Token usage
- Cost
- Latency
- Relevance scores
```

### **4. Conversation History**
```python
# DynamoDB with TTL:
- Stores all exchanges
- 30-day auto-deletion
- Query by conversation_id
```

---

## 📊 **Feature Comparison**

| Feature | Required | Status | Enhancement |
|---------|----------|--------|-------------|
| **Vector Search** | ✅ Yes | ✅ Complete | KNN + cosine similarity |
| **Hybrid Search** | ✅ Yes | ✅ Complete | 70/30 vector/keyword |
| **Context Optimization** | ✅ Yes | ✅ Complete | Multi-tier selection |
| **Dynamic Prompts** | ✅ Yes | ✅ Complete | Adaptive construction |
| **Bedrock Integration** | ✅ Yes | ✅ Complete | 4 models |
| PII Detection | ❌ Bonus | ✅ Complete | AWS Comprehend |
| Re-ranking | ❌ Bonus | ✅ Complete | Heuristic-based |
| Cost Tracking | ❌ Bonus | ✅ Complete | Per-model |
| Monitoring | ❌ Bonus | ✅ Complete | CloudWatch |
| Evaluation | ❌ Bonus | ✅ Complete | DynamoDB logging |

---

## 🚀 **API Response Example**

```json
{
  "request_id": "abc-123-def",
  "conversation_id": "conv-456",
  "response": "AWS Lambda is a serverless compute service...",
  "model": "anthropic.claude-3-sonnet-20240229-v1:0",
  "model_tier": "advanced",
  "latency": 1.234,
  "tokens": {
    "prompt": 847,
    "response": 156,
    "total": 1003
  },
  "cost": 0.022,
  "has_pii": false,
  "sources": [
    {
      "document_id": "doc-123",
      "score": 0.92
    },
    {
      "document_id": "doc-456", 
      "score": 0.85
    }
  ]
}
```

---

## 🎯 **How Each Feature Works Together**

```
User Query
    ↓
1. PII Detection (safety check)
    ↓
2. Generate Embedding (Titan)
    ↓
3. Hybrid Search (Vector 70% + Keyword 30%)
    ↓
4. Re-rank Results (optimization)
    ↓
5. Select Model Tier (cost optimization)
    ↓
6. Construct Dynamic Prompt (context building)
    ↓
7. Invoke Bedrock Model (generation)
    ↓
8. Count Tokens & Calculate Cost
    ↓
9. Store Conversation & Metrics
    ↓
10. Return Enhanced Response
```

---

## 💡 **Key Advantages**

### **1. Cost Efficiency**
- Uses cheaper models for simple queries
- Tracks every dollar spent
- Optimizes context length

### **2. Better Accuracy**
- Hybrid search improves recall
- Re-ranking refines results
- Context-aware responses

### **3. Production Ready**
- Comprehensive monitoring
- Error handling
- PII detection
- Evaluation metrics

### **4. Flexible**
- Configurable model selection
- Adjustable weights
- Optional hybrid search
- Streaming support (ready)

---

## 🔧 **Configuration Options**

```python
# In handler function:
relevant_chunks = retrieve_relevant_chunks(
    query,
    max_results=5,        # Number of chunks
    use_hybrid=True       # Enable/disable hybrid search
)

# Model selection can be:
# - Automatic (based on query complexity)
# - Manual (specify model_tier in request)
```

---

## ✅ **Summary**

**ALL 5 Required Features:** ✅ **COMPLETE**

1. ✅ Vector Search - Full KNN implementation
2. ✅ Hybrid Search - Vector + Keyword (NEW!)
3. ✅ Context Optimization - Multi-tier, re-ranking, token mgmt
4. ✅ Dynamic Prompts - Adaptive, conversation-aware
5. ✅ Bedrock Integration - 4 models, dynamic selection

**Plus 5 Bonus Features:**
- PII Detection
- Re-ranking Algorithm
- Comprehensive Monitoring
- Cost Tracking
- Evaluation Data Storage

**Status:** 🎯 Production-ready with advanced features!
