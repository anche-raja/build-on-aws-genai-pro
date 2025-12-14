#!/bin/bash
# Quick trace script for your recent PDF upload

echo "==================================="
echo "Tracing Your Recent PDF Upload"
echo "==================================="
echo ""

# Step 1: Find your most recent upload
echo "1. Finding your recent uploads..."
RECENT_FILES=$(aws s3 ls s3://gka-documents-284244381060/public/uploads/anche.raja@gmail.com/ --recursive | tail -5)
echo "$RECENT_FILES"
echo ""

# Get the most recent file
LATEST_FILE=$(echo "$RECENT_FILES" | tail -1 | awk '{print $NF}')
echo "Most recent file: $LATEST_FILE"
echo ""

# Step 2: Search Lambda logs
echo "2. Searching Lambda logs (last 1 hour)..."
echo ""

# macOS compatible date command
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  ONE_HOUR_AGO=$(date -u -v-1H +%s)000
  ONE_DAY_AGO=$(date -u -v-24H +%s)000
else
  # Linux
  ONE_HOUR_AGO=$(date -u -d '1 hour ago' +%s)000
  ONE_DAY_AGO=$(date -u -d '24 hours ago' +%s)000
fi

LAMBDA_OUTPUT=$(aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-document-processor \
  --start-time $ONE_HOUR_AGO \
  --filter-pattern '"anche.raja"' \
  --max-items 50 \
  --query 'events[*].message' \
  --output text)

if [ -z "$LAMBDA_OUTPUT" ]; then
  echo "⚠ No logs found in last hour. Trying last 24 hours..."
  LAMBDA_OUTPUT=$(aws logs filter-log-events \
    --log-group-name /aws/lambda/gka-document-processor \
    --start-time $ONE_DAY_AGO \
    --filter-pattern '"anche.raja"' \
    --max-items 50 \
    --query 'events[*].message' \
    --output text)
fi

if [ -n "$LAMBDA_OUTPUT" ]; then
  echo "✓ Found Lambda processing logs:"
  echo ""
  echo "$LAMBDA_OUTPUT" | head -30
  echo ""
  
  # Try to extract document_id
  DOCUMENT_ID=$(echo "$LAMBDA_OUTPUT" | grep -o '"document_id":"[^"]*"' | head -1 | cut -d'"' -f4)
  
  if [ -n "$DOCUMENT_ID" ]; then
    echo "=========================================="
    echo "📄 Document ID: $DOCUMENT_ID"
    echo "=========================================="
    echo ""
    
    # Step 3: Check DynamoDB
    echo "3. Checking DynamoDB metadata..."
    aws dynamodb get-item \
      --table-name gka-metadata \
      --key "{\"document_id\": {\"S\": \"$DOCUMENT_ID\"}}" \
      --output json | jq '{
        document_id: .Item.document_id.S,
        document_key: .Item.document_key.S,
        chunk_count: .Item.chunk_count.N,
        total_tokens: .Item.total_tokens.N,
        timestamp: .Item.timestamp.S
      }'
    echo ""
    
    # Step 4: Check OpenSearch
    echo "4. Checking OpenSearch index..."
    cd ~/build-on-aws-genai-pro/enterprise_genai_knowledge_assistant/iac
    
    # Get OpenSearch credentials
    SECRET_ARN=$(terraform output -raw opensearch_password_secret_arn 2>/dev/null)
    if [ -n "$SECRET_ARN" ]; then
      CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text)
      USERNAME=$(echo $CREDENTIALS | jq -r .username)
      PASSWORD=$(echo $CREDENTIALS | jq -r .password)
      OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint 2>/dev/null)
      
      if [ -n "$OPENSEARCH_ENDPOINT" ]; then
        # Count chunks
        RESULT=$(curl -s -u $USERNAME:$PASSWORD \
          "https://$OPENSEARCH_ENDPOINT/documents/_count" \
          -H 'Content-Type: application/json' \
          -d "{\"query\": {\"match\": {\"metadata.document_id\": \"$DOCUMENT_ID\"}}}")
        
        CHUNK_COUNT=$(echo $RESULT | jq -r '.count')
        echo "✓ Found $CHUNK_COUNT chunks indexed in OpenSearch"
        echo ""
        
        # Show first chunk
        echo "Sample chunk preview:"
        curl -s -u $USERNAME:$PASSWORD \
          "https://$OPENSEARCH_ENDPOINT/documents/_search" \
          -H 'Content-Type: application/json' \
          -d "{
            \"query\": {\"match\": {\"metadata.document_id\": \"$DOCUMENT_ID\"}},
            \"size\": 1,
            \"_source\": [\"content\", \"metadata.chunk_index\", \"metadata.tokens\"]
          }" | jq '.hits.hits[0]._source'
      else
        echo "⚠ Could not get OpenSearch endpoint"
      fi
    else
      echo "⚠ Could not get OpenSearch credentials"
    fi
  else
    echo "⚠ Could not extract document_id from logs"
    echo ""
    echo "Raw log sample:"
    echo "$LAMBDA_OUTPUT" | head -10
  fi
else
  echo "✗ No processing logs found for your uploads"
  echo ""
  echo "Possible reasons:"
  echo "  - Document was uploaded but not processed yet"
  echo "  - Check if /documents API was called"
  echo "  - Lambda may have failed to trigger"
fi

echo ""
echo "==================================="
echo "Trace Complete"
echo "==================================="
echo ""
echo "💡 For more detailed tracing, see: DOCUMENT_FLOW_TRACING.md"
