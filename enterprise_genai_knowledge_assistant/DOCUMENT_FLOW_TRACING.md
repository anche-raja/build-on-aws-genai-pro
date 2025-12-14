# Document Flow Tracing Guide

Complete guide to trace a document through the entire processing pipeline.

---

## Document Processing Flow

```
User Upload (Web App)
    ↓
S3 Bucket (gka-documents-284244381060)
    ↓
API Gateway (/documents endpoint)
    ↓
Document Processor Lambda (gka-document-processor)
    ├→ Retrieve from S3
    ├→ Chunk document (semantic chunking)
    ├→ Generate embeddings (Amazon Titan)
    ├→ Index to OpenSearch (vector + metadata)
    └→ Store metadata in DynamoDB (gka-metadata)
```

---

## Step-by-Step Tracing

### Step 1: Find Your Document in S3

```bash
# List recent uploads (last 1 hour)
aws s3 ls s3://gka-documents-284244381060/public/uploads/ --recursive \
  | awk '{if (NR>1) {print $NF}}' \
  | tail -20

# Or search by your email
aws s3 ls s3://gka-documents-284244381060/public/uploads/anche.raja@gmail.com/ --recursive

# Download the document to verify
aws s3 cp s3://gka-documents-284244381060/public/uploads/anche.raja@gmail.com/YOUR_FILE.pdf /tmp/
```

**What to note:**
- Document key (full S3 path)
- Upload timestamp
- File size

---

### Step 2: Check API Gateway Logs

```bash
# View recent API Gateway logs
aws logs tail /aws/apigateway/gka --follow --since 1h

# Filter for document processing requests
aws logs filter-log-events \
  --log-group-name /aws/apigateway/gka \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern '"POST /documents"'

# Get specific request details
aws logs filter-log-events \
  --log-group-name /aws/apigateway/gka \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern '"YOUR_FILE.pdf"'
```

**What to look for:**
- Request ID
- HTTP status (200 = success)
- Request body (contains `document_key`)
- Response time

---

### Step 3: Check Document Processor Lambda Logs

This is the main processing step!

```bash
# Tail Lambda logs in real-time
aws logs tail /aws/lambda/gka-document-processor --follow

# View last 1 hour of logs
aws logs tail /aws/lambda/gka-document-processor --since 1h

# Search for your specific document
aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-document-processor \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern '"YOUR_FILE.pdf"'

# Or search by document_key pattern
aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-document-processor \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern '"anche.raja"' \
  | jq -r '.events[].message'
```

**Key log entries to find:**

1. **Document Retrieval:**
   ```
   Getting document from S3: gka-documents-284244381060/public/uploads/...
   ```

2. **Chunking:**
   ```
   Processing document: chunks=X, total_tokens=Y
   ```

3. **Embedding Generation:**
   ```
   Generating embedding for chunk...
   ```

4. **OpenSearch Indexing:**
   ```
   Indexing X chunks in OpenSearch
   ```

5. **Success:**
   ```
   Document processed successfully
   ```

**Common Errors to Watch For:**
- `Document not found in S3`
- `Failed to generate embedding`
- `OpenSearch connection error`
- `DynamoDB write error`

---

### Step 4: Find Your Document ID

From the Lambda logs, you'll see:

```json
{
  "status": "success",
  "document_id": "abc123-def456-...",
  "chunk_count": 5,
  "total_tokens": 1500
}
```

**Save this `document_id` - you'll need it for the next steps!**

---

### Step 5: Check DynamoDB Metadata Table

```bash
# Get document metadata
aws dynamodb get-item \
  --table-name gka-metadata \
  --key '{"document_id": {"S": "YOUR_DOCUMENT_ID"}}'

# Or scan for recent documents
aws dynamodb scan \
  --table-name gka-metadata \
  --filter-expression "contains(document_key, :key)" \
  --expression-attribute-values '{":key":{"S":"YOUR_FILE.pdf"}}' \
  --max-items 5

# Prettier output with jq
aws dynamodb scan \
  --table-name gka-metadata \
  --max-items 10 \
  | jq '.Items[] | {
      document_id: .document_id.S,
      document_key: .document_key.S,
      chunk_count: .chunk_count.N,
      timestamp: .timestamp.S
    }'
```

**What you'll see:**
```json
{
  "document_id": "abc123-...",
  "document_key": "public/uploads/anche.raja@gmail.com/YOUR_FILE.pdf",
  "chunk_count": 5,
  "total_tokens": 1500,
  "timestamp": "2025-12-13T...",
  "document_type": "pdf"
}
```

---

### Step 6: Check OpenSearch Index

```bash
# Get OpenSearch credentials
SECRET_ARN=$(cd ~/build-on-aws-genai-pro/enterprise_genai_knowledge_assistant/iac && terraform output -raw opensearch_password_secret_arn)
CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text)
USERNAME=$(echo $CREDENTIALS | jq -r .username)
PASSWORD=$(echo $CREDENTIALS | jq -r .password)
OPENSEARCH_ENDPOINT=$(cd ~/build-on-aws-genai-pro/enterprise_genai_knowledge_assistant/iac && terraform output -raw opensearch_endpoint)

# Search for your document in OpenSearch
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {
        "metadata.document_id": "YOUR_DOCUMENT_ID"
      }
    }
  }' | jq .

# Count how many chunks were indexed
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_count" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {
        "metadata.document_id": "YOUR_DOCUMENT_ID"
      }
    }
  }' | jq .

# View a specific chunk
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {
        "metadata.document_id": "YOUR_DOCUMENT_ID"
      }
    },
    "size": 1
  }' | jq '.hits.hits[0]._source'
```

**What you'll see:**
```json
{
  "content": "Chunk text here...",
  "embedding": [0.123, 0.456, ...],  // 1536 dimensions
  "metadata": {
    "document_id": "abc123-...",
    "chunk_index": 0,
    "tokens": 250
  }
}
```

---

## Complete Trace Script

Save this script to trace any document:

```bash
#!/bin/bash
# trace-document.sh - Trace a document through the pipeline

DOCUMENT_KEY="$1"  # e.g., "public/uploads/anche.raja@gmail.com/Resume-Raja.pdf"

if [ -z "$DOCUMENT_KEY" ]; then
  echo "Usage: ./trace-document.sh <document_key>"
  echo "Example: ./trace-document.sh 'public/uploads/anche.raja@gmail.com/Resume-Raja.pdf'"
  exit 1
fi

echo "==================================="
echo "Tracing Document: $DOCUMENT_KEY"
echo "==================================="
echo ""

# Step 1: Check S3
echo "1. Checking S3..."
aws s3 ls s3://gka-documents-284244381060/$DOCUMENT_KEY 2>/dev/null
if [ $? -eq 0 ]; then
  echo "✓ Found in S3"
else
  echo "✗ NOT found in S3"
fi
echo ""

# Step 2: Find in Lambda logs
echo "2. Searching Lambda logs..."
LAMBDA_LOGS=$(aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-document-processor \
  --start-time $(date -u -d '24 hours ago' +%s)000 \
  --filter-pattern "\"$DOCUMENT_KEY\"" \
  --query 'events[*].message' \
  --output text \
  | head -20)

if [ -n "$LAMBDA_LOGS" ]; then
  echo "✓ Found in Lambda logs"
  echo "$LAMBDA_LOGS"
  
  # Extract document_id
  DOCUMENT_ID=$(echo "$LAMBDA_LOGS" | grep -o '"document_id":"[^"]*"' | head -1 | cut -d'"' -f4)
  if [ -n "$DOCUMENT_ID" ]; then
    echo ""
    echo "Document ID: $DOCUMENT_ID"
  fi
else
  echo "✗ NOT found in Lambda logs (check if processed in last 24h)"
fi
echo ""

# Step 3: Check DynamoDB
if [ -n "$DOCUMENT_ID" ]; then
  echo "3. Checking DynamoDB..."
  aws dynamodb get-item \
    --table-name gka-metadata \
    --key "{\"document_id\": {\"S\": \"$DOCUMENT_ID\"}}" \
    --query 'Item' \
    --output json | jq .
  echo ""
  
  # Step 4: Check OpenSearch
  echo "4. Checking OpenSearch..."
  cd ~/build-on-aws-genai-pro/enterprise_genai_knowledge_assistant/iac
  SECRET_ARN=$(terraform output -raw opensearch_password_secret_arn)
  CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text)
  USERNAME=$(echo $CREDENTIALS | jq -r .username)
  PASSWORD=$(echo $CREDENTIALS | jq -r .password)
  OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
  
  CHUNK_COUNT=$(curl -s -u $USERNAME:$PASSWORD \
    "https://$OPENSEARCH_ENDPOINT/documents/_count" \
    -H 'Content-Type: application/json' \
    -d "{\"query\": {\"match\": {\"metadata.document_id\": \"$DOCUMENT_ID\"}}}" \
    | jq -r '.count')
  
  echo "✓ Found $CHUNK_COUNT chunks in OpenSearch"
else
  echo "3-4. Skipping DynamoDB/OpenSearch check (no document_id found)"
fi

echo ""
echo "==================================="
echo "Trace Complete"
echo "==================================="
```

**Usage:**
```bash
chmod +x trace-document.sh
./trace-document.sh "public/uploads/anche.raja@gmail.com/Resume-Raja.pdf"
```

---

## Quick Commands for Your Recent Upload

Replace `YOUR_FILE.pdf` with your actual filename:

```bash
# 1. Find your document
aws s3 ls s3://gka-documents-284244381060/public/uploads/anche.raja@gmail.com/ --recursive

# 2. Get Lambda logs for last hour
aws logs tail /aws/lambda/gka-document-processor --since 1h | grep -i "anche.raja"

# 3. Find document_id
aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-document-processor \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern '"document_id"' \
  | jq -r '.events[].message' | grep -A 5 "anche.raja"

# 4. Once you have document_id, check everything
DOCUMENT_ID="paste-your-document-id-here"

# DynamoDB
aws dynamodb get-item --table-name gka-metadata --key "{\"document_id\": {\"S\": \"$DOCUMENT_ID\"}}"

# OpenSearch count
# (Use the OpenSearch commands from above)
```

---

## CloudWatch Insights Queries

For advanced analysis, use CloudWatch Insights:

```sql
-- Find all document processing events
fields @timestamp, @message
| filter @message like /Document processed successfully/
| sort @timestamp desc
| limit 20

-- Find processing errors
fields @timestamp, @message
| filter @message like /error/
| sort @timestamp desc
| limit 20

-- Average processing time
fields @timestamp, @message
| filter @message like /Duration:/
| parse @message /Duration: (?<duration>\d+.\d+) ms/
| stats avg(duration) as avg_duration, max(duration) as max_duration

-- Find your specific document
fields @timestamp, @message
| filter @message like /anche.raja/
| sort @timestamp desc
```

---

## Troubleshooting

### Document not showing in OpenSearch?

1. **Check Lambda errors:**
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/gka-document-processor \
     --start-time $(date -u -d '1 hour ago' +%s)000 \
     --filter-pattern "ERROR"
   ```

2. **Check OpenSearch cluster health:**
   ```bash
   curl -u $USERNAME:$PASSWORD "https://$OPENSEARCH_ENDPOINT/_cluster/health"
   ```

3. **Verify Lambda has OpenSearch permissions:**
   ```bash
   aws iam get-role-policy \
     --role-name gka-lambda-execution-role \
     --policy-name gka-services-policy
   ```

### Document not in DynamoDB?

```bash
# Check Lambda execution role has DynamoDB permissions
aws iam get-role-policy \
  --role-name gka-lambda-execution-role \
  --policy-name gka-services-policy | jq '.PolicyDocument.Statement[] | select(.Action[] | contains("dynamodb"))'
```

---

**Last Updated:** December 13, 2025
