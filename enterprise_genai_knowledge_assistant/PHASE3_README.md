# Phase 3: RAG System Implementation - README

## 🎯 **Overview**

Phase 3 implements the Retrieval-Augmented Generation (RAG) system, which is the core intelligence of the GenAI Knowledge Assistant. It combines advanced search techniques with Foundation Models to provide accurate, contextual responses.

---

## 🚀 **Quick Start**

### **Test the RAG System:**

```bash
# Set API endpoint
API_URL=$(terraform output -raw api_url)

# Send a query
curl -X POST "${API_URL}/query" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What is AWS Lambda?",
    "user_id": "test@example.com"
  }'
```

### **Expected Response:**

```json
{
  "request_id": "abc-123-def",
  "conversation_id": "conv-456",
  "response": "AWS Lambda is a serverless compute service...",
  "model": "anthropic.claude-v2",
  "latency": 1.234,
  "tokens": {
    "prompt": 1500,
    "response": 250,
    "total": 1750
  },
  "cost": 0.015,
  "sources": [
    {"document_id": "doc-1", "score": 0.92},
    {"document_id": "doc-2", "score": 0.85}
  ],
  "quality_scores": {
    "relevance": 0.92,
    "coherence": 0.85,
    "overall": 0.88
  }
}
```

---

## 📋 **Features**

### **1. Vector Search (Semantic)**
- Uses Amazon Titan Embeddings
- 1536-dimensional vectors
- Cosine similarity matching
- Finds conceptually similar content

### **2. Keyword Search (Lexical)**
- BM25 algorithm
- Exact keyword matching
- Handles specific terms and phrases

### **3. Hybrid Search**
- Combines vector + keyword results
- 70% semantic, 30% lexical weighting
- Best of both worlds

### **4. Re-ranking**
- Keyword density analysis
- Length optimization
- Position bonuses
- Quality scoring

### **5. Context Optimization**
- Token counting with tiktoken
- Fits within model limits
- Prioritizes most relevant chunks

### **6. Dynamic Prompts**
- Adapts to query complexity
- Includes conversation history
- Provides clear instructions

### **7. Bedrock Integration**
- Multiple model support
- Automatic fallback
- Cost optimization

---

## 🔧 **Configuration**

### **Search Parameters:**

Edit `lambda/query_handler/app.py`:

```python
# Vector search
VECTOR_SEARCH_K = 10          # Top K results
VECTOR_WEIGHT = 0.7           # 70% weight

# Keyword search
KEYWORD_SEARCH_K = 10         # Top K results
KEYWORD_WEIGHT = 0.3          # 30% weight

# Final selection
FINAL_K = 5                   # Chunks to include in context
MIN_SCORE_THRESHOLD = 0.3     # Minimum relevance score
```

### **Context Limits:**

```python
# Token budgets
MAX_TOTAL_TOKENS = 4000       # Total context limit
RESERVE_TOKENS = 1600         # For prompt + history + query
MAX_CHUNK_TOKENS = 800        # Single chunk limit

# Context optimization
INCLUDE_METADATA = True       # Show source info
INCLUDE_HISTORY = True        # Include conversation
MAX_HISTORY_EXCHANGES = 3     # Last N exchanges
```

### **Model Selection:**

```python
# Simple queries (< 10 words, no complex indicators)
SIMPLE_MODEL = "anthropic.claude-instant-v1"
SIMPLE_MAX_TOKENS = 500
SIMPLE_TEMPERATURE = 0.2

# Standard queries (10-20 words, or complex indicators)
STANDARD_MODEL = "anthropic.claude-v2"
STANDARD_MAX_TOKENS = 1000
STANDARD_TEMPERATURE = 0.7

# Advanced queries (> 20 words, technical terms)
ADVANCED_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"
ADVANCED_MAX_TOKENS = 2000
ADVANCED_TEMPERATURE = 0.7
```

---

## 📊 **How It Works**

### **Step-by-Step Process:**

#### **1. Query Received**
```
Input: "What is AWS Lambda and how does it work?"
```

#### **2. Vector Search**
```python
# Generate embedding
query_embedding = titan_embeddings.embed(query)
# Shape: [1536]

# Search OpenSearch
vector_results = opensearch.knn_search(
    embedding=query_embedding,
    k=10
)
# Returns: 10 chunks with similarity scores
```

#### **3. Keyword Search**
```python
# Multi-match query
keyword_results = opensearch.multi_match(
    query="AWS Lambda how does it work",
    fields=["text"],
    k=10
)
# Returns: 10 chunks with BM25 scores
```

#### **4. Hybrid Fusion**
```python
# Combine results
combined = []
for chunk in vector_results:
    combined.append({
        'chunk': chunk,
        'score': chunk['vector_score'] * 0.7 + 
                chunk.get('keyword_score', 0) * 0.3
    })

# Sort by combined score
combined.sort(key=lambda x: x['score'], reverse=True)
# Result: Unified ranked list
```

#### **5. Re-ranking**
```python
# Apply quality factors
for chunk in combined:
    score = chunk['score']
    
    # Keyword density boost
    if has_query_keywords(chunk, query):
        score *= 1.1
    
    # Length penalty
    if 100 <= word_count(chunk) <= 500:
        score *= 1.1
    
    chunk['final_score'] = score

# Select top 5
top_chunks = combined[:5]
```

#### **6. Context Optimization**
```python
# Count tokens
selected_chunks = []
total_tokens = 0

for chunk in top_chunks:
    tokens = count_tokens(chunk['text'])
    if total_tokens + tokens <= 2400:  # Budget
        selected_chunks.append(chunk)
        total_tokens += tokens

# Result: 3-5 chunks within budget
```

#### **7. Prompt Construction**
```python
prompt = f"""You are a helpful knowledge assistant.

CONTEXT:
{format_chunks(selected_chunks)}

QUESTION:
{query}

ANSWER:"""

# Token count: ~2000 total
```

#### **8. Model Invocation**
```python
# Select model (Phase 4 logic)
model = select_model(query)  # "claude-v2"

# Invoke Bedrock
response = bedrock.invoke_model(
    modelId=model,
    body={
        "prompt": prompt,
        "max_tokens": 1000,
        "temperature": 0.7
    }
)

# Result: Generated response
```

#### **9. Response**
```
Output: "AWS Lambda is a serverless compute service that 
         lets you run code without provisioning servers. 
         It executes your code only when needed and scales
         automatically..."
```

---

## 🎯 **Usage Examples**

### **Example 1: Simple Query**

**Query:**
```json
{
  "query": "What is S3?",
  "user_id": "user@example.com"
}
```

**Process:**
- Model: Claude Instant (simple)
- Chunks: 2-3 (short context)
- Latency: ~800ms
- Cost: ~$0.005

**Response:**
```
"Amazon S3 (Simple Storage Service) is an object storage 
service that offers industry-leading scalability, data 
availability, security, and performance."
```

### **Example 2: Complex Query**

**Query:**
```json
{
  "query": "Compare AWS Lambda and EC2 for serverless applications. What are the cost implications and when should I use each?",
  "user_id": "user@example.com"
}
```

**Process:**
- Model: Claude 3 Sonnet (advanced)
- Chunks: 5 (full context)
- Latency: ~2500ms
- Cost: ~$0.035

**Response:**
```
"AWS Lambda vs EC2 for Serverless Applications:

Lambda:
- Pay only for compute time
- Auto-scales automatically
- No server management
- Best for: Event-driven, short-duration tasks

EC2:
- Pay for instance uptime
- Manual or auto-scaling
- Full server control
- Best for: Long-running processes, custom configurations

Cost Implications:
[Detailed comparison based on retrieved documents]"
```

### **Example 3: Multi-turn Conversation**

**Turn 1:**
```json
{
  "query": "What is DynamoDB?",
  "user_id": "user@example.com"
}
```

**Response 1:**
```
"Amazon DynamoDB is a fully managed NoSQL database service 
that provides fast and predictable performance..."
```

**Turn 2:**
```json
{
  "query": "How does it compare to RDS?",
  "user_id": "user@example.com",
  "conversation_id": "conv-123"
}
```

**Response 2:**
```
"Comparing DynamoDB to RDS:

DynamoDB (NoSQL):
- Schema-less
- Horizontal scaling
- Millisecond latency
- Best for: Key-value, document data

RDS (SQL):
- Fixed schema
- Vertical scaling
- Complex queries
- Best for: Relational data, ACID transactions"
```

---

## 📈 **Performance Tuning**

### **Optimize Search Quality:**

```python
# Increase search breadth
VECTOR_SEARCH_K = 20  # More initial results
KEYWORD_SEARCH_K = 20

# Adjust weights for your use case
VECTOR_WEIGHT = 0.8   # More semantic (general queries)
# OR
VECTOR_WEIGHT = 0.5   # More balanced (technical queries)

# Stricter filtering
MIN_SCORE_THRESHOLD = 0.5  # Higher quality bar
```

### **Optimize for Speed:**

```python
# Reduce search scope
VECTOR_SEARCH_K = 5   # Fewer results
FINAL_K = 3           # Fewer chunks

# Use simpler model
DEFAULT_MODEL = "claude-instant-v1"

# Reduce max tokens
MAX_TOKENS = 300      # Shorter responses
```

### **Optimize for Cost:**

```python
# Aggressive caching
CACHE_TTL = 3600      # 1 hour

# Prefer simple model
MODEL_TIER_THRESHOLD_SIMPLE = 20  # More queries → simple
MODEL_TIER_THRESHOLD_ADVANCED = 30  # Fewer → advanced

# Reduce context
FINAL_K = 3           # Fewer chunks = lower cost
```

---

## 🔍 **Troubleshooting**

### **Issue: Low Relevance Scores**

**Symptoms:**
- Responses not relevant to query
- Low quality scores
- Users reporting inaccurate answers

**Solutions:**
```python
# 1. Increase search breadth
VECTOR_SEARCH_K = 15
KEYWORD_SEARCH_K = 15

# 2. Lower threshold
MIN_SCORE_THRESHOLD = 0.2

# 3. Adjust hybrid weights
VECTOR_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4  # More keyword matching

# 4. Check document quality
# - Are documents properly chunked?
# - Are embeddings generated correctly?
# - Is OpenSearch index healthy?
```

### **Issue: High Latency**

**Symptoms:**
- Queries take > 3 seconds
- Timeout errors
- Poor user experience

**Solutions:**
```python
# 1. Reduce search scope
VECTOR_SEARCH_K = 5
FINAL_K = 3

# 2. Enable caching
CACHE_ENABLED = True
CACHE_TTL = 1800  # 30 minutes

# 3. Use simpler model
DEFAULT_MODEL = "claude-instant-v1"

# 4. Check OpenSearch performance
# - Increase instance size
# - Add read replicas
# - Optimize index settings
```

### **Issue: High Costs**

**Symptoms:**
- Monthly Bedrock costs high
- Budget exceeded
- Need cost optimization

**Solutions:**
```python
# 1. Increase cache hit rate
CACHE_TTL = 3600  # 1 hour

# 2. Use model tiering aggressively
# Send more queries to simple model

# 3. Reduce token usage
MAX_TOKENS = 500  # Shorter responses
FINAL_K = 3       # Less context

# 4. Monitor and alert
# Set up CloudWatch cost alarms
```

---

## 📊 **Monitoring**

### **Key Metrics to Track:**

#### **Search Quality:**
```
- Average relevance score
- Search result count
- Hybrid score distribution
- Re-ranking improvement
```

#### **Response Quality:**
```
- User feedback (thumbs up/down)
- Quality scores (6 dimensions)
- Groundedness (sources used)
- Response length
```

#### **Performance:**
```
- Query latency (P50, P95, P99)
- Search latency
- Model invocation latency
- Cache hit rate
```

#### **Cost:**
```
- Cost per query
- Model tier distribution
- Token usage
- Cache savings
```

### **CloudWatch Queries:**

```sql
-- Average relevance score
fields @timestamp, relevance_score
| stats avg(relevance_score) by bin(5m)

-- Query latency percentiles
fields @timestamp, latency
| stats pct(latency, 50), pct(latency, 95), pct(latency, 99)

-- Model tier distribution
fields @timestamp, model_tier
| stats count() by model_tier

-- Cost per hour
fields @timestamp, cost
| stats sum(cost) by bin(1h)
```

---

## ✅ **Testing**

### **Unit Tests:**

```python
# Test vector search
def test_vector_search():
    results = vector_search("AWS Lambda", k=10)
    assert len(results) == 10
    assert all(r['score'] > 0 for r in results)

# Test hybrid fusion
def test_hybrid_fusion():
    vector_results = [...]
    keyword_results = [...]
    combined = combine_results(vector_results, keyword_results)
    assert len(combined) >= len(vector_results)

# Test context optimization
def test_context_optimization():
    chunks = [...]
    selected, tokens = optimize_context(chunks, max_tokens=2000)
    assert tokens < 2000
```

### **Integration Tests:**

```bash
# Test simple query
curl -X POST "$API_URL/query" -d '{"query":"What is S3?"}'

# Test complex query
curl -X POST "$API_URL/query" -d '{"query":"Compare Lambda vs EC2"}'

# Test conversation
curl -X POST "$API_URL/query" -d '{"query":"What is DynamoDB?"}'
curl -X POST "$API_URL/query" -d '{"query":"How does it scale?", "conversation_id":"..."}'
```

---

## 📚 **References**

- **AWS Documentation:**
  - [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)
  - [Amazon OpenSearch](https://docs.aws.amazon.com/opensearch-service/)
  - [Amazon Titan Embeddings](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)

- **Research Papers:**
  - [Retrieval-Augmented Generation (RAG)](https://arxiv.org/abs/2005.11401)
  - [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
  - [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)

- **Best Practices:**
  - [Prompt Engineering Guide](https://www.promptingguide.ai/)
  - [RAG Best Practices](https://aws.amazon.com/blogs/machine-learning/best-practices-for-rag/)

---

## 🎯 **Next Steps**

1. **Test the system** with your own documents and queries
2. **Tune parameters** based on your use case
3. **Monitor metrics** in CloudWatch dashboards
4. **Collect feedback** from users
5. **Iterate and improve** based on data

---

## ✅ **Phase 3 Implementation Complete!**

You now have a production-ready RAG system with:
- ✅ Hybrid search (semantic + keyword)
- ✅ Intelligent re-ranking
- ✅ Context optimization
- ✅ Dynamic prompt construction
- ✅ Multiple model support
- ✅ Conversation continuity
- ✅ Performance monitoring

**Happy querying! 🚀**

