# Phase 2: Document Processing Pipeline - README

## 🎯 **Quick Start**

Process documents through the intelligent chunking and embedding pipeline.

### **Prerequisites:**
- ✅ Phase 1 infrastructure deployed
- ✅ Documents uploaded to S3
- ✅ Bedrock model access enabled (Titan Embeddings)

### **Process a Document:**

```bash
# 1. Upload document to S3
aws s3 cp my-document.txt s3://gka-documents-123456/uploads/

# 2. Trigger processing
API_URL=$(cd iac && terraform output -raw api_url)

curl -X POST "${API_URL}/documents" \
  -H 'Content-Type: application/json' \
  -d '{
    "document_key": "uploads/my-document.txt",
    "document_type": "text"
  }'

# 3. Response
{
  "document_id": "doc-abc-123",
  "chunk_count": 8,
  "total_tokens": 6500
}
```

---

## 📋 **Document Processing Features**

### **1. S3 Document Ingestion** ✅
- Retrieves documents from S3
- Supports text and PDF formats
- UTF-8 decoding
- Error handling for missing files

### **2. Dynamic Semantic Chunking** ✅
- **Strategy:** Paragraph-based
- **Max size:** 1000 tokens per chunk
- **Boundary:** Double newlines (\n\n)
- **Preserves:** Semantic context

### **3. Token Counting** ✅
- **Library:** tiktoken
- **Encoding:** cl100k_base
- **Accuracy:** Matches Claude/GPT-4
- **Purpose:** Cost calculation, chunk sizing

### **4. Embedding Generation** ✅
- **Model:** Amazon Titan Embeddings v1
- **Dimension:** 1536
- **Cost:** $0.0001 per 1K tokens
- **Latency:** 80-120ms per chunk

### **5. OpenSearch Vector Indexing** ✅
- **Index:** document-chunks
- **Algorithm:** HNSW (Hierarchical NSW)
- **Similarity:** Cosine
- **Engine:** FAISS

### **6. Metadata Management** ✅
- **Storage:** DynamoDB
- **Tracking:** Chunk counts, tokens, status
- **Queryable:** By document ID or S3 key

---

## 🔧 **Configuration**

### **Chunking Configuration:**

Edit `lambda/document_processor/app.py`:

```python
# Chunk size limit
MAX_CHUNK_TOKENS = 1000  # Default

# For different document types:
CHUNK_SIZES = {
    "technical": 1500,  # More context for technical docs
    "faq": 300,         # Short for FAQs
    "article": 1000,    # Standard for articles
    "book": 2000        # Longer for books/manuals
}

# Use based on document type
max_tokens = CHUNK_SIZES.get(document_type, 1000)
```

### **Embedding Configuration:**

```python
# Model selection
EMBEDDING_MODEL = "amazon.titan-embed-text-v1"
EMBEDDING_DIMENSION = 1536

# Batch processing (for large documents)
BATCH_SIZE = 10  # Process 10 chunks in parallel

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
BACKOFF_FACTOR = 2  # exponential backoff
```

### **OpenSearch Configuration:**

```python
# Index settings
INDEX_NAME = "document-chunks"
KNN_METHOD = "hnsw"
KNN_SPACE_TYPE = "cosinesimil"
KNN_EF_CONSTRUCTION = 512  # Build quality
KNN_M = 16                 # Graph connectivity

# Search settings
DEFAULT_K = 10             # Number of results
MIN_SCORE = 0.3            # Minimum similarity score
```

---

## 📊 **Processing Examples**

### **Example 1: Small Document (1 KB)**

**Input:**
```
File: quick-start.txt
Size: 1 KB
Tokens: 500
Content: Quick start guide for AWS Lambda
```

**Processing:**
```
Retrieve from S3:     50ms
Chunking:             10ms
Token counting:       5ms
Embedding (1 chunk):  100ms
OpenSearch indexing:  50ms
Metadata storage:     20ms
──────────────────────────
Total:               235ms
Cost:                $0.00005
```

**Output:**
```json
{
  "document_id": "doc-001",
  "chunk_count": 1,
  "total_tokens": 500
}
```

---

### **Example 2: Medium Document (10 KB)**

**Input:**
```
File: lambda-best-practices.txt
Size: 10 KB
Tokens: 5000
Content: Comprehensive Lambda guide with examples
```

**Processing:**
```
Retrieve from S3:     60ms
Chunking:             15ms
Token counting:       25ms
Embedding (5 chunks): 500ms (parallel)
OpenSearch indexing:  250ms
Metadata storage:     20ms
──────────────────────────
Total:               870ms
Cost:                $0.0005
```

**Output:**
```json
{
  "document_id": "doc-002",
  "chunk_count": 5,
  "total_tokens": 5000
}
```

**Chunks Created:**
```
Chunk 1: Introduction + Overview (980 tokens)
Chunk 2: Best Practices (950 tokens)
Chunk 3: Performance Optimization (1000 tokens)
Chunk 4: Security Guidelines (890 tokens)
Chunk 5: Monitoring & Logging (1180 tokens)
```

---

### **Example 3: Large Document (100 KB)**

**Input:**
```
File: aws-whitepaper.txt
Size: 100 KB
Tokens: 50,000
Content: Complete AWS architectural whitepaper
```

**Processing:**
```
Retrieve from S3:     200ms
Chunking:             100ms
Token counting:       200ms
Embedding (50 chunks): 5s (parallel batches)
OpenSearch indexing:  2.5s
Metadata storage:     30ms
──────────────────────────
Total:               8.03s
Cost:                $0.005
```

**Output:**
```json
{
  "document_id": "doc-003",
  "chunk_count": 50,
  "total_tokens": 50000
}
```

---

## 🧪 **Testing**

### **Test 1: Upload and Process Document**

```bash
# Create test document
cat > test-doc.txt <<EOF
AWS Lambda is a serverless compute service.

It lets you run code without provisioning servers.

You pay only for the compute time you consume.

Lambda automatically scales your application.
EOF

# Upload to S3
aws s3 cp test-doc.txt s3://gka-documents-123456/test/

# Process
curl -X POST "${API_URL}/documents" \
  -H 'Content-Type: application/json' \
  -d '{
    "document_key": "test/test-doc.txt",
    "document_type": "text"
  }'

# Expected response
{
  "document_id": "doc-...",
  "chunk_count": 1,
  "total_tokens": 30
}
```

### **Test 2: Verify Chunks in OpenSearch**

```bash
# Get OpenSearch credentials
SECRET=$(cd iac && terraform output -raw opensearch_master_user_secret)
PASSWORD=$(aws secretsmanager get-secret-value --secret-id ${SECRET} --query SecretString --output text | jq -r .password)

# Query index
curl -u admin:${PASSWORD} \
  "https://vpc-gka-vector-search-abc.us-east-1.es.amazonaws.com/document-chunks/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {"match_all": {}},
    "size": 10
  }'
```

### **Test 3: Verify Metadata in DynamoDB**

```bash
# Query metadata table
aws dynamodb scan \
  --table-name gka-metadata \
  --max-items 10

# Get specific document
aws dynamodb get-item \
  --table-name gka-metadata \
  --key '{"id": {"S": "doc-abc-123"}}'
```

### **Test 4: Check Processing Logs**

```bash
# View document processor logs
aws logs tail /aws/lambda/gka-document-processor \
  --follow \
  --format short

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-document-processor \
  --filter-pattern "ERROR"
```

---

## 📈 **Monitoring**

### **Key Metrics:**

```bash
# Documents processed (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=gka-document-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Average processing time
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=gka-document-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average

# Processing errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=gka-document-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

### **Custom Metrics:**

Add to `lambda/document_processor/app.py`:

```python
import boto3
cloudwatch = boto3.client('cloudwatch')

# After processing
cloudwatch.put_metric_data(
    Namespace='GenAI/DocumentProcessing',
    MetricData=[
        {
            'MetricName': 'ChunksGenerated',
            'Value': len(chunks),
            'Unit': 'Count'
        },
        {
            'MetricName': 'TokensProcessed',
            'Value': total_tokens,
            'Unit': 'Count'
        },
        {
            'MetricName': 'ProcessingTime',
            'Value': processing_time,
            'Unit': 'Seconds'
        }
    ]
)
```

---

## 🔍 **Querying Processed Documents**

### **List All Documents:**

```bash
aws dynamodb scan \
  --table-name gka-metadata \
  --projection-expression "id,document_key,chunk_count,total_tokens"
```

### **Get Document Details:**

```bash
aws dynamodb get-item \
  --table-name gka-metadata \
  --key '{"id": {"S": "doc-abc-123"}}' \
  | jq '.Item'
```

### **Search by S3 Key:**

```bash
aws dynamodb query \
  --table-name gka-metadata \
  --index-name DocumentKeyIndex \
  --key-condition-expression "document_key = :key" \
  --expression-attribute-values '{":key": {"S": "uploads/my-doc.txt"}}'
```

### **Count Total Documents:**

```bash
aws dynamodb scan \
  --table-name gka-metadata \
  --select COUNT
```

---

## 💰 **Cost Tracking**

### **Per-Document Cost:**

```
Document Size    Chunks    Tokens    Embedding Cost    Total
───────────────────────────────────────────────────────────────
1 KB             1         500       $0.00005          $0.00005
5 KB             3         2,500     $0.00025          $0.00025
10 KB            5         5,000     $0.00050          $0.00050
50 KB            25        25,000    $0.00250          $0.00250
100 KB           50        50,000    $0.00500          $0.00500
```

**Additional Costs:**
- Lambda invocation: $0.0000002 per request
- DynamoDB write: $0.00000125 per write
- OpenSearch indexing: Included in cluster cost
- S3 storage: $0.023 per GB/month

### **Monthly Processing Cost:**

```
Scenario: 1000 documents/month (average 10 KB each)

Embeddings: 1000 docs × $0.0005  = $0.50
Lambda:     1000 invocations     = $0.0002
DynamoDB:   1000 writes          = $0.00125
────────────────────────────────────────────
Total:                           = $0.50/month

Plus infrastructure: $282/month
Grand total: $282.50/month
```

---

## 🚀 **Bulk Document Processing**

### **Upload Multiple Documents:**

```bash
# Upload a folder of documents
aws s3 sync ./documents/ s3://gka-documents-123456/batch-upload/

# Process all documents
for file in documents/*.txt; do
  filename=$(basename "$file")
  curl -X POST "${API_URL}/documents" \
    -H 'Content-Type: application/json' \
    -d "{
      \"document_key\": \"batch-upload/${filename}\",
      \"document_type\": \"text\"
    }"
  sleep 1  # Rate limiting
done
```

### **Batch Processing Script:**

```python
# batch_process.py
import boto3
import requests
import os

s3 = boto3.client('s3')
bucket = 'gka-documents-123456'
api_url = os.environ['API_URL']

# List all objects in S3
response = s3.list_objects_v2(Bucket=bucket, Prefix='batch-upload/')

for obj in response.get('Contents', []):
    key = obj['Key']
    
    # Trigger processing
    resp = requests.post(
        f"{api_url}/documents",
        json={
            'document_key': key,
            'document_type': 'text'
        }
    )
    
    print(f"Processed {key}: {resp.json()}")
```

---

## 🔍 **Troubleshooting**

### **Issue: Document not found in S3**

**Error:**
```json
{
  "statusCode": 404,
  "body": "{\"error\": \"Document not found\"}"
}
```

**Solution:**
```bash
# 1. Check if file exists
aws s3 ls s3://gka-documents-123456/uploads/my-document.txt

# 2. Check Lambda has S3 permissions
aws iam get-role-policy \
  --role-name gka-lambda-execution-role \
  --policy-name gka-lambda-execution-policy \
  | jq '.PolicyDocument.Statement[] | select(.Action[] | contains("s3"))'

# 3. Check S3 bucket policy
aws s3api get-bucket-policy \
  --bucket gka-documents-123456
```

---

### **Issue: Chunking produces unexpected results**

**Problem:** Too many small chunks or too few large chunks

**Debug:**
```python
# Add logging in app.py
def process_text_document(text):
    paragraphs = text.split('\n\n')
    print(f"Total paragraphs: {len(paragraphs)}")
    
    for i, para in enumerate(paragraphs):
        tokens = len(tokenizer.encode(para))
        print(f"Paragraph {i}: {tokens} tokens, {len(para)} chars")
```

**Solutions:**
```python
# Solution 1: Adjust max tokens
MAX_CHUNK_TOKENS = 1500  # Larger chunks

# Solution 2: Different splitting
# For documents without clear paragraphs:
paragraphs = text.split('\n')  # Split by single newline

# For documents with sections:
sections = re.split(r'\n#{1,3}\s', text)  # Split by markdown headers
```

---

### **Issue: Embedding generation fails**

**Error:**
```
ThrottlingException: Rate exceeded for InvokeModel
```

**Solution:**
```python
# Add retry with exponential backoff
import time
from botocore.exceptions import ClientError

def generate_embedding_with_retry(text, max_retries=5):
    for attempt in range(max_retries):
        try:
            return generate_embedding(text)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
            else:
                raise
```

**Prevention:**
```bash
# Request quota increase
# AWS Console → Service Quotas → Amazon Bedrock
# Request: "Invocations per minute for Titan Embeddings"
# Increase from 1000 to 5000
```

---

### **Issue: OpenSearch indexing slow**

**Problem:** Indexing takes > 500ms per chunk

**Diagnosis:**
```bash
# Check OpenSearch cluster health
aws opensearch describe-domain \
  --domain-name gka-vector-search \
  | jq '.DomainStatus.ClusterConfig'

# Check CPU usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/ES \
  --metric-name CPUUtilization \
  --dimensions Name=DomainName,Value=gka-vector-search \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

**Solutions:**
```python
# Solution 1: Use bulk API
from opensearchpy import helpers

actions = [
    {
        "_index": "document-chunks",
        "_id": chunk['id'],
        "_source": {
            "document_id": document_id,
            "text": chunk['text'],
            "embedding": chunk['embedding']
        }
    }
    for chunk in chunks
]

helpers.bulk(opensearch_client, actions)

# Solution 2: Increase refresh interval during bulk indexing
opensearch_client.indices.put_settings(
    index="document-chunks",
    body={"index": {"refresh_interval": "30s"}}
)

# After indexing, reset
opensearch_client.indices.put_settings(
    index="document-chunks",
    body={"index": {"refresh_interval": "1s"}}
)
```

---

## 📊 **Performance Optimization**

### **Parallel Processing:**

```python
# Process chunks in parallel
from concurrent.futures import ThreadPoolExecutor

def process_chunks_parallel(chunks, max_workers=10):
    """
    Generate embeddings in parallel
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = [
            executor.submit(generate_embedding, chunk['text'])
            for chunk in chunks
        ]
        
        # Collect results
        for i, future in enumerate(futures):
            chunks[i]['embedding'] = future.result()
    
    return chunks

# Reduces processing time by ~80% for large documents
```

### **Caching Embeddings:**

```python
# Cache embeddings for identical chunks
import hashlib

EMBEDDING_CACHE = {}

def generate_embedding_cached(text):
    """
    Generate embedding with caching
    """
    # Generate hash of text
    text_hash = hashlib.md5(text.encode()).hexdigest()
    
    # Check cache
    if text_hash in EMBEDDING_CACHE:
        return EMBEDDING_CACHE[text_hash]
    
    # Generate and cache
    embedding = generate_embedding(text)
    EMBEDDING_CACHE[text_hash] = embedding
    
    return embedding
```

---

## ✅ **Verification Checklist**

After processing documents, verify:

- [ ] Document retrieved from S3 successfully
- [ ] Chunks created (check count matches expectation)
- [ ] Token counts accurate (matches tiktoken)
- [ ] Embeddings generated (1536 dimensions)
- [ ] Chunks indexed in OpenSearch
- [ ] Metadata stored in DynamoDB
- [ ] No errors in CloudWatch Logs
- [ ] Processing time acceptable (< 10s for 100 KB)
- [ ] Costs within budget

---

## 🎓 **Best Practices**

### **Document Preparation:**
- ✅ Use UTF-8 encoding
- ✅ Clean formatting (remove extra whitespace)
- ✅ Consistent paragraph breaks
- ✅ Remove boilerplate (headers, footers)
- ✅ Split very large documents (> 1 MB)

### **Chunking Strategy:**
- ✅ Keep chunk size 500-1500 tokens
- ✅ Preserve semantic boundaries
- ✅ Don't split mid-sentence
- ✅ Include context (don't over-chunk)

### **Error Handling:**
- ✅ Implement retry logic for embeddings
- ✅ Handle missing documents gracefully
- ✅ Log errors to CloudWatch
- ✅ Return meaningful error messages

### **Performance:**
- ✅ Process embeddings in parallel
- ✅ Use bulk OpenSearch API
- ✅ Monitor processing time
- ✅ Set appropriate Lambda memory

---

## 📚 **References**

- **Semantic Chunking:** [Best Practices Guide](https://aws.amazon.com/blogs/machine-learning/chunking-strategies/)
- **Titan Embeddings:** [Model Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- **OpenSearch KNN:** [KNN Plugin Guide](https://opensearch.org/docs/latest/search-plugins/knn/)
- **tiktoken:** [GitHub Repository](https://github.com/openai/tiktoken)

---

## ✅ **Phase 2 Complete!**

You can now:
- ✅ Upload documents to S3
- ✅ Process them through intelligent chunking
- ✅ Generate high-quality embeddings
- ✅ Index in vector database
- ✅ Track metadata and status
- ✅ Monitor processing performance

**Ready for Phase 3: RAG System!** 🚀

