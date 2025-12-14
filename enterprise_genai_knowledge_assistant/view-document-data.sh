#!/bin/bash
# View document embeddings and metadata

DOCUMENT_ID="$1"

echo "==================================="
echo "Document Data Viewer"
echo "==================================="
echo ""

# If no document_id provided, show recent documents
if [ -z "$DOCUMENT_ID" ]; then
  echo "📚 Recent Documents in DynamoDB:"
  echo ""
  aws dynamodb scan \
    --table-name gka-metadata \
    --max-items 10 \
    --query 'Items[*].[document_id.S, document_key.S, chunk_count.N, timestamp.S]' \
    --output table
  echo ""
  echo "Usage: $0 <document_id>"
  echo "Copy a document_id from above and run:"
  echo "  $0 abc123-def456-..."
  exit 0
fi

echo "🔍 Viewing Document: $DOCUMENT_ID"
echo ""

# ============================================
# 1. DynamoDB Metadata
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  DynamoDB METADATA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

METADATA=$(aws dynamodb get-item \
  --table-name gka-metadata \
  --key "{\"document_id\": {\"S\": \"$DOCUMENT_ID\"}}" \
  --output json)

if [ "$(echo $METADATA | jq -r '.Item')" == "null" ]; then
  echo "❌ Document not found in DynamoDB"
  exit 1
fi

echo "$METADATA" | jq '.Item | {
  document_id: .document_id.S,
  document_key: .document_key.S,
  document_type: .document_type.S,
  chunk_count: .chunk_count.N,
  total_tokens: .total_tokens.N,
  timestamp: .timestamp.S,
  chunks: .chunks.L | length
}'

echo ""

# ============================================
# 2. OpenSearch - Get Credentials
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  OpenSearch EMBEDDINGS & CHUNKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd ~/build-on-aws-genai-pro/enterprise_genai_knowledge_assistant/iac

SECRET_ARN=$(terraform output -raw opensearch_password_secret_arn 2>/dev/null)
if [ -z "$SECRET_ARN" ]; then
  echo "❌ Could not get OpenSearch credentials"
  exit 1
fi

CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text)
USERNAME=$(echo $CREDENTIALS | jq -r .username)
PASSWORD=$(echo $CREDENTIALS | jq -r .password)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint 2>/dev/null)

# Count total chunks
CHUNK_COUNT=$(curl -s -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_count" \
  -H 'Content-Type: application/json' \
  -d "{\"query\": {\"match\": {\"metadata.document_id\": \"$DOCUMENT_ID\"}}}" \
  | jq -r '.count')

echo "📦 Total Chunks Indexed: $CHUNK_COUNT"
echo ""

# Get all chunks with embeddings
echo "📄 Fetching all chunks..."
echo ""

CHUNKS=$(curl -s -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_search" \
  -H 'Content-Type: application/json' \
  -d "{
    \"query\": {
      \"match\": {
        \"metadata.document_id\": \"$DOCUMENT_ID\"
      }
    },
    \"size\": $CHUNK_COUNT,
    \"sort\": [{\"metadata.chunk_index\": \"asc\"}]
  }")

# Display chunks overview
echo "$CHUNKS" | jq -r '
  .hits.hits[] | 
  "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
  "Chunk \(._source.metadata.chunk_index)",
  "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
  "Tokens: \(._source.metadata.tokens)",
  "Content Preview: \(._source.content[:200])...",
  "Embedding Vector (first 10 dimensions): \(._source.embedding[:10])",
  "Embedding Length: \(._source.embedding | length) dimensions",
  ""
'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  DETAILED CHUNK DATA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Prompt user for detailed view
echo "💡 View detailed data for a specific chunk? (y/n)"
read -r RESPONSE

if [[ "$RESPONSE" =~ ^[Yy]$ ]]; then
  echo ""
  echo "Enter chunk index (0-$((CHUNK_COUNT-1))):"
  read -r CHUNK_INDEX
  
  echo ""
  echo "Full Chunk Data:"
  echo ""
  
  echo "$CHUNKS" | jq ".hits.hits[] | select(._source.metadata.chunk_index == $CHUNK_INDEX) | {
    chunk_index: ._source.metadata.chunk_index,
    tokens: ._source.metadata.tokens,
    content: ._source.content,
    embedding_sample: ._source.embedding[:20],
    embedding_length: (._source.embedding | length),
    full_metadata: ._source.metadata
  }"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  SAVE TO FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "💾 Save full data to files? (y/n)"
read -r SAVE_RESPONSE

if [[ "$SAVE_RESPONSE" =~ ^[Yy]$ ]]; then
  OUTPUT_DIR="document_data_$DOCUMENT_ID"
  mkdir -p "$OUTPUT_DIR"
  
  # Save metadata
  echo "$METADATA" | jq '.Item' > "$OUTPUT_DIR/metadata.json"
  echo "✓ Saved: $OUTPUT_DIR/metadata.json"
  
  # Save all chunks
  echo "$CHUNKS" | jq '.hits.hits[] | ._source' > "$OUTPUT_DIR/chunks_with_embeddings.json"
  echo "✓ Saved: $OUTPUT_DIR/chunks_with_embeddings.json"
  
  # Save chunks without embeddings (easier to read)
  echo "$CHUNKS" | jq '[.hits.hits[] | {
    chunk_index: ._source.metadata.chunk_index,
    tokens: ._source.metadata.tokens,
    content: ._source.content,
    embedding_dimensions: (._source.embedding | length)
  }]' > "$OUTPUT_DIR/chunks_readable.json"
  echo "✓ Saved: $OUTPUT_DIR/chunks_readable.json"
  
  # Save just content
  echo "$CHUNKS" | jq -r '.hits.hits[] | "=== Chunk \(._source.metadata.chunk_index) ===\n\(._source.content)\n"' > "$OUTPUT_DIR/content_only.txt"
  echo "✓ Saved: $OUTPUT_DIR/content_only.txt"
  
  # Save sample embedding
  echo "$CHUNKS" | jq '.hits.hits[0] | {
    chunk_0_embedding: .embedding,
    dimensions: (.embedding | length),
    sample_values: .embedding[:50]
  }' > "$OUTPUT_DIR/sample_embedding.json"
  echo "✓ Saved: $OUTPUT_DIR/sample_embedding.json"
  
  echo ""
  echo "📁 All files saved to: $OUTPUT_DIR/"
  echo ""
  echo "Files created:"
  ls -lh "$OUTPUT_DIR/"
fi

echo ""
echo "==================================="
echo "✓ Complete"
echo "==================================="
