#!/bin/bash
# Manually trigger document processing for an already uploaded file

DOCUMENT_KEY="$1"

if [ -z "$DOCUMENT_KEY" ]; then
  echo "Usage: ./process-uploaded-doc.sh <document_key>"
  echo ""
  echo "Recent uploads:"
  aws s3 ls s3://gka-documents-284244381060/public/uploads/anche.raja@gmail.com/ --recursive | tail -5
  echo ""
  echo "Copy the full path after the date/time, for example:"
  echo "./process-uploaded-doc.sh 'public/uploads/anche.raja@gmail.com/1765671130739-Resume-Raja.pdf'"
  exit 1
fi

API_URL="https://3chov1t2di.execute-api.us-east-1.amazonaws.com/prod"

echo "Processing document: $DOCUMENT_KEY"
echo ""

# Call the API Gateway endpoint
RESPONSE=$(curl -s -X POST "$API_URL/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_key\": \"$DOCUMENT_KEY\",
    \"document_type\": \"pdf\"
  }")

echo "Response:"
echo "$RESPONSE" | jq .

# Extract document_id if successful
DOCUMENT_ID=$(echo "$RESPONSE" | jq -r '.document_id // empty')

if [ -n "$DOCUMENT_ID" ]; then
  echo ""
  echo "✓ Document processed successfully!"
  echo "Document ID: $DOCUMENT_ID"
  echo ""
  echo "Waiting 5 seconds for indexing to complete..."
  sleep 5
  echo ""
  echo "Checking DynamoDB..."
  aws dynamodb get-item \
    --table-name gka-metadata \
    --key "{\"document_id\": {\"S\": \"$DOCUMENT_ID\"}}" \
    | jq '.Item | {
        document_id: .document_id.S,
        chunk_count: .chunk_count.N,
        total_tokens: .total_tokens.N
      }'
else
  echo ""
  echo "✗ Processing failed or returned error"
  echo "Check the response above for details"
fi
