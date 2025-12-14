# Operations Guide - GenAI Knowledge Assistant

Complete guide for monitoring, testing, troubleshooting, and maintaining the system.

---

## Table of Contents

1. [Monitoring & Observability](#monitoring--observability)
2. [Testing & Validation](#testing--validation)
3. [Troubleshooting](#troubleshooting)
4. [Maintenance](#maintenance)
5. [Performance Tuning](#performance-tuning)
6. [Security Operations](#security-operations)

---

## Monitoring & Observability

### CloudWatch Dashboards

#### 1. Main Dashboard (gka)

**Access:**
```bash
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=gka"
```

**Widgets:**
- **Performance**: Lambda invocations, duration, errors, throttles
- **API Gateway**: Requests, 4XX/5XX errors, latency (p50, p90, p99)
- **Cost Tracking**: Token usage, model tier distribution, estimated daily cost
- **Caching**: Cache hit rate, cache size, TTL expirations
- **OpenSearch**: CPU utilization, JVM memory, search latency, indexing rate
- **DynamoDB**: Read/write capacity, throttled requests, item count

#### 2. Governance Dashboard (gka-governance)

**Widgets:**
- **Safety**: PII detections by type, guardrail blocks by category
- **Compliance**: Audit events logged, exports completed
- **Alerts**: Recent SNS notifications, alarm state changes
- **Audit Trail**: Events per hour, severity distribution

#### 3. Quality Dashboard (gka-quality)

**Widgets:**
- **Quality Scores**: Overall quality trend, dimension breakdown
- **User Feedback**: Thumbs up/down ratio, star ratings, comment count
- **Satisfaction**: Net Promoter Score (NPS), satisfaction trend
- **Evaluations**: Average scores by model tier, quality distribution

### CloudWatch Logs

**Log Groups:**

```bash
# Lambda function logs
/aws/lambda/gka-document-processor
/aws/lambda/gka-query-handler
/aws/lambda/gka-quality-reporter
/aws/lambda/gka-analytics-exporter
/aws/lambda/gka-audit-exporter

# Governance logs
/aws/governance/gka

# Quality logs
/aws/quality/gka

# API Gateway logs
API-Gateway-Execution-Logs_<api-id>/prod
```

**Tail logs in real-time:**
```bash
# Document processor
aws logs tail /aws/lambda/gka-document-processor --follow

# Query handler
aws logs tail /aws/lambda/gka-query-handler --follow --filter-pattern "ERROR"

# All Lambda errors
aws logs tail /aws/lambda/gka-* --follow --filter-pattern "ERROR"
```

**Query logs (CloudWatch Insights):**
```sql
-- Find slow queries (>3 seconds)
fields @timestamp, query, latency
| filter @message like /Query processed/
| filter latency > 3000
| sort @timestamp desc
| limit 20

-- PII detection events
fields @timestamp, pii_types, redacted_count
| filter @message like /PII detected/
| stats count() by pii_types

-- Model tier usage
fields @timestamp, model_tier, query
| filter @message like /Model selected/
| stats count() by model_tier

-- Errors by type
fields @timestamp, error_type, @message
| filter @message like /ERROR/
| stats count() by error_type
```

### Custom CloudWatch Metrics

**Namespace: GenAI/KnowledgeAssistant**

```python
# Query metrics
QueryComplexity           # 0-100 (complexity score)
QueryLatency              # milliseconds
QueryCost                 # USD
QuerySuccess              # 0/1

# Prompt metrics
PromptTokens              # count
ResponseTokens            # count
TotalTokens               # count

# Response metrics
ResponseQuality           # 0-1 (quality score)
CacheHitRate              # 0-1

# Model metrics
ModelTierUsed             # simple/standard/advanced
ModelFallbacks            # count
```

**Namespace: GenAI/Governance**

```python
PIIDetected               # count (by type)
PIIRedacted               # count
GuardrailBlocked          # count (by category)
AuditEventsLogged         # count
ComplianceAlertsTriggered # count
```

### CloudWatch Alarms

**View alarm status:**
```bash
# List all alarms
aws cloudwatch describe-alarms --alarm-name-prefix gka-

# Check specific alarm
aws cloudwatch describe-alarms --alarm-names gka-pii-detected
```

**Active Alarms:**

| Alarm | Threshold | Action |
|-------|-----------|--------|
| gka-pii-detected | >5 in 5 min | SNS compliance alert |
| gka-guardrail-blocked | >10 in 5 min | SNS compliance alert |
| gka-lambda-errors | >10 in 5 min | SNS quality alert |
| gka-high-latency | >3000ms avg | SNS quality alert |
| gka-low-quality | <0.7 avg score | SNS quality alert |
| gka-high-cost | >$100 daily | SNS compliance alert |

### SNS Alerts

**Subscribe to alerts:**
```bash
# Get topic ARNs
cd iac
COMPLIANCE_TOPIC=$(terraform output -raw compliance_alerts_topic)
QUALITY_TOPIC=$(terraform output -raw quality_alerts_topic)

# Subscribe with email
aws sns subscribe \
  --topic-arn $COMPLIANCE_TOPIC \
  --protocol email \
  --notification-endpoint your-email@example.com

aws sns subscribe \
  --topic-arn $QUALITY_TOPIC \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription (check email)
```

**Test alerts:**
```bash
# Publish test message
aws sns publish \
  --topic-arn $COMPLIANCE_TOPIC \
  --subject "Test Alert" \
  --message "This is a test compliance alert"
```

### End-to-End Tracing

**Lambda Request Tracing:**

Each Lambda invocation generates a unique request ID. Track it across services:

```bash
# Get request ID from response
REQUEST_ID="abc123-def456-ghi789"

# Search across all logs
aws logs tail /aws/lambda/gka-* --follow --filter-pattern "$REQUEST_ID"
```

**Correlation IDs:**

For multi-step flows (document upload → processing → indexing):

```python
# Lambda generates correlation ID
correlation_id = f"doc_{document_id}_{timestamp}"

# Log with correlation ID
logger.info(f"[{correlation_id}] Starting document processing")

# Search logs
aws logs tail /aws/lambda/gka-document-processor \
  --filter-pattern "doc_12345_*"
```

**X-Ray Integration (Optional):**

Enable AWS X-Ray for distributed tracing:

```bash
# Add to Lambda environment variables
AWS_XRAY_TRACING_ENABLED=true

# View service map
open "https://console.aws.amazon.com/xray/home?region=us-east-1#/service-map"
```

---

## Testing & Validation

### Document Upload Testing

**Test 1: Upload via API**

```bash
# Get API URL and credentials
cd iac
API_URL=$(terraform output -raw api_gateway_url)
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)

# Create test document in S3
echo "This is a test document about AWS Lambda functions. Lambda is a serverless compute service." > test.txt

# Upload to S3
BUCKET=$(terraform output -raw document_bucket_name)
aws s3 cp test.txt s3://$BUCKET/test.txt

# Trigger processing
curl -X POST ${API_URL}/documents \
  -H "Content-Type: application/json" \
  -d '{
    "document_key": "test.txt",
    "document_type": "text/plain",
    "metadata": {
      "title": "Test Document",
      "author": "Test User"
    }
  }'
```

**Test 2: Verify Processing**

```bash
# Check Lambda logs
aws logs tail /aws/lambda/gka-document-processor --follow

# Check OpenSearch index
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
SECRET_ARN=$(terraform output -raw opensearch_password_secret_arn)
CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text)
USERNAME=$(echo $CREDENTIALS | jq -r .username)
PASSWORD=$(echo $CREDENTIALS | jq -r .password)

# Query index
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_search?q=Lambda"

# Check DynamoDB metadata
METADATA_TABLE=$(terraform output -raw metadata_table_name)
aws dynamodb scan --table-name $METADATA_TABLE --max-items 5
```

**Test 3: Verify Chunking**

```bash
# Upload large document
cat <<EOF > large_test.txt
# AWS Lambda Overview

AWS Lambda is a serverless compute service that runs your code in response to events and automatically manages the underlying compute resources for you.

## Key Features

Lambda automatically scales your application by running code in response to each event. Your code runs in parallel and processes each trigger individually.

## Use Cases

Lambda is ideal for:
- Data processing
- Real-time file processing
- Web applications
- Mobile backends
EOF

aws s3 cp large_test.txt s3://$BUCKET/large_test.txt

# Trigger and check chunking
curl -X POST ${API_URL}/documents \
  -H "Content-Type: application/json" \
  -d '{"document_key": "large_test.txt", "document_type": "text/plain"}'

# Query OpenSearch to see chunks
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"metadata.document_id": "large_test.txt"}}}'
```

### Query Testing

**Test 1: Simple Query**

```bash
# Test query via API
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is AWS Lambda?",
    "conversation_id": "test-conv-001"
  }'

# Expected response:
# {
#   "response": "...",
#   "sources": [...],
#   "model_tier": "simple",
#   "quality_score": 0.85
# }
```

**Test 2: Complex Query (Advanced Model)**

```bash
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare AWS Lambda with traditional server-based architectures, considering scalability, cost, and operational overhead.",
    "conversation_id": "test-conv-002"
  }'

# Should use "advanced" tier (Claude 3 Sonnet)
```

**Test 3: Conversation History**

```bash
# First query
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Lambda?",
    "conversation_id": "test-conv-003"
  }'

# Follow-up query (uses history)
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How much does it cost?",
    "conversation_id": "test-conv-003"
  }'
```

**Test 4: Cache Hit**

```bash
# First query (cache miss)
time curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Lambda?", "conversation_id": "test-cache-001"}'

# Second identical query (cache hit, should be faster)
time curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Lambda?", "conversation_id": "test-cache-002"}'
```

### Safety & Governance Testing

**Test 1: PII Detection**

```bash
# Query with PII
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My SSN is 123-45-6789 and my email is test@example.com",
    "conversation_id": "test-pii-001"
  }'

# Check governance logs
aws logs tail /aws/governance/gka --follow --filter-pattern "PII detected"

# Check CloudWatch metric
aws cloudwatch get-metric-statistics \
  --namespace GenAI/Governance \
  --metric-name PIIDetected \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Test 2: Guardrails (Harmful Content)**

```bash
# Query with harmful content (adjust based on your guardrail config)
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to hack into a system?",
    "conversation_id": "test-guardrail-001"
  }'

# Should be blocked by guardrails
# Expected response:
# {
#   "error": "Request blocked by content guardrails",
#   "reason": "GUARDRAIL_INTERVENED"
# }

# Check governance dashboard
```

**Test 3: Audit Logging**

```bash
# Make several queries
for i in {1..5}; do
  curl -X POST ${API_URL}/query \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Test query $i\", \"conversation_id\": \"test-audit-$i\"}"
done

# Check audit trail in DynamoDB
AUDIT_TABLE=$(terraform output -raw audit_trail_table_name)
aws dynamodb scan --table-name $AUDIT_TABLE --max-items 10

# Check S3 exports (wait for daily export)
AUDIT_BUCKET=$(terraform output -raw audit_logs_bucket_name)
aws s3 ls s3://$AUDIT_BUCKET/audit-exports/ --recursive
```

### Quality Metrics Testing

**Test 1: Submit Feedback**

```bash
# Submit positive feedback
curl -X POST ${API_URL}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "query-123",
    "rating": 5,
    "thumbs": "up",
    "comment": "Great response!"
  }'

# Submit negative feedback
curl -X POST ${API_URL}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "query-456",
    "rating": 2,
    "thumbs": "down",
    "comment": "Response was not relevant"
  }'

# Check feedback table
FEEDBACK_TABLE=$(terraform output -raw user_feedback_table_name)
aws dynamodb scan --table-name $FEEDBACK_TABLE --max-items 10
```

**Test 2: Quality Reports**

```bash
# Manually trigger quality reporter
aws lambda invoke \
  --function-name gka-quality-reporter \
  --payload '{}' \
  output.json

cat output.json

# Check S3 for report
ANALYTICS_BUCKET=$(terraform output -raw analytics_exports_bucket_name)
aws s3 ls s3://$ANALYTICS_BUCKET/quality-reports/

# Download latest report
aws s3 cp s3://$ANALYTICS_BUCKET/quality-reports/$(date +%Y-%m-%d).json .
cat $(date +%Y-%m-%d).json | jq .
```

### Load Testing

**Basic Load Test:**

```bash
# Install Apache Bench
# brew install httpd (macOS) or apt-get install apache2-utils (Linux)

# Prepare test payload
cat <<EOF > query_payload.json
{"query": "What is AWS Lambda?", "conversation_id": "load-test"}
EOF

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -p query_payload.json -T application/json \
  ${API_URL}/query

# Check results
# - Requests per second
# - Time per request (mean)
# - Failed requests
```

**Advanced Load Test (Artillery):**

```bash
# Install Artillery
npm install -g artillery

# Create test scenario
cat <<EOF > load-test.yml
config:
  target: "${API_URL}"
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Sustained load"
scenarios:
  - name: "Query flow"
    flow:
      - post:
          url: "/query"
          json:
            query: "What is Lambda?"
            conversation_id: "{{ \$randomString() }}"
EOF

# Run load test
artillery run load-test.yml

# Review metrics
```

---

## Troubleshooting

### Common Issues

#### 1. Document Upload Returns 502

**Symptoms:**
- API returns 502 Bad Gateway
- No response from Lambda

**Diagnosis:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/gka-document-processor --follow

# Common errors:
# - "Unable to import module" → Missing dependencies
# - "Task timed out" → Lambda timeout (increase)
# - "OpenSearch connection failed" → Credentials or network issue
```

**Resolution:**
```bash
# Rebuild Lambda with dependencies
./build-lambda.sh

# Update Lambda function
cd lambda/document_processor/package
zip -r ../deploy.zip .
aws lambda update-function-code \
  --function-name gka-document-processor \
  --zip-file fileb://../deploy.zip

# Increase timeout if needed
aws lambda update-function-configuration \
  --function-name gka-document-processor \
  --timeout 300
```

#### 2. Query Returns Empty Results

**Symptoms:**
- Query succeeds but returns no relevant documents
- "No context found" in response

**Diagnosis:**
```bash
# Check if documents are indexed
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_count"

# Check OpenSearch index mappings
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/documents/_mapping"

# Check metadata table
aws dynamodb scan --table-name $METADATA_TABLE --max-items 10
```

**Resolution:**
```bash
# Reindex documents
for key in $(aws s3 ls s3://$BUCKET/ | awk '{print $4}'); do
  curl -X POST ${API_URL}/documents \
    -H "Content-Type: application/json" \
    -d "{\"document_key\": \"$key\", \"document_type\": \"text/plain\"}"
done

# Check OpenSearch cluster health
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/_cluster/health"
```

#### 3. High Latency (>3 seconds)

**Symptoms:**
- Queries take >3 seconds to complete
- Users report slow responses

**Diagnosis:**
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace GenAI/KnowledgeAssistant \
  --metric-name QueryLatency \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Check OpenSearch latency
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/_cluster/stats?human&pretty"

# Check Lambda cold starts
aws logs tail /aws/lambda/gka-query-handler --follow --filter-pattern "Duration"
```

**Resolution:**
```bash
# Enable caching (if not already)
# Increase Lambda memory (more CPU)
aws lambda update-function-configuration \
  --function-name gka-query-handler \
  --memory-size 2048

# Use provisioned concurrency (reduce cold starts)
aws lambda put-provisioned-concurrency-config \
  --function-name gka-query-handler \
  --provisioned-concurrent-executions 5 \
  --qualifier $LATEST

# Scale OpenSearch (add nodes or upgrade instance type)
```

#### 4. PII Redaction Not Working

**Symptoms:**
- PII visible in responses or logs
- No PII detection metrics

**Diagnosis:**
```bash
# Check Comprehend permissions
aws iam get-role-policy \
  --role-name gka-lambda-execution-role \
  --policy-name comprehend-access

# Test PII detection directly
aws comprehend detect-pii-entities \
  --text "My SSN is 123-45-6789" \
  --language-code en

# Check governance logs
aws logs tail /aws/governance/gka --follow --filter-pattern "PII"
```

**Resolution:**
```bash
# Ensure IAM permissions
# Verify Lambda environment variable ENABLE_PII_DETECTION=true
# Check Lambda code for PII detection logic

# Redeploy Lambda if needed
./build-lambda.sh
# ... update function code
```

#### 5. Guardrails Not Blocking Content

**Symptoms:**
- Harmful content not blocked
- No guardrail metrics

**Diagnosis:**
```bash
# Check guardrail configuration
GUARDRAIL_ID=$(terraform output -raw guardrail_id)
aws bedrock get-guardrail --guardrail-identifier $GUARDRAIL_ID

# Check Lambda environment variable
aws lambda get-function-configuration \
  --function-name gka-query-handler | jq .Environment.Variables.GUARDRAIL_ID

# Test guardrail directly
aws bedrock-runtime apply-guardrail \
  --guardrail-identifier $GUARDRAIL_ID \
  --guardrail-version 1 \
  --source INPUT \
  --content '[{"text": {"text": "harmful content here"}}]'
```

**Resolution:**
```bash
# Update guardrail configuration in Terraform
# Redeploy: cd iac && terraform apply

# Verify Lambda has correct GUARDRAIL_ID
# Redeploy Lambda if needed
```

---

## Maintenance

### Regular Maintenance Tasks

#### Daily
- [ ] Review CloudWatch dashboards (errors, performance)
- [ ] Check SNS alerts (compliance, quality)
- [ ] Verify scheduled tasks ran (EventBridge logs)
- [ ] Check audit exports (S3 bucket)

#### Weekly
- [ ] Review quality metrics (trends, user feedback)
- [ ] Check cost and usage (CloudWatch billing)
- [ ] Review OpenSearch cluster health
- [ ] Check DynamoDB capacity (throttling, item counts)
- [ ] Review Lambda cold start metrics

#### Monthly
- [ ] Review and rotate credentials (OpenSearch, Cognito)
- [ ] Clean up old DynamoDB items (TTL policy review)
- [ ] Review S3 storage costs (lifecycle policies)
- [ ] Update dependencies (Lambda, web app)
- [ ] Security audit (IAM policies, access logs)
- [ ] Performance review (latency, quality trends)

### Data Retention Policies

**DynamoDB Tables:**
```bash
# Set TTL on conversations (90 days)
aws dynamodb update-time-to-live \
  --table-name gka-conversations \
  --time-to-live-specification "Enabled=true, AttributeName=ttl"

# Set TTL on evaluations (180 days)
aws dynamodb update-time-to-live \
  --table-name gka-evaluations \
  --time-to-live-specification "Enabled=true, AttributeName=ttl"
```

**S3 Lifecycle Policies:**
```bash
# Archive audit logs to Glacier after 1 year
aws s3api put-bucket-lifecycle-configuration \
  --bucket $AUDIT_BUCKET \
  --lifecycle-configuration file://lifecycle-policy.json

# lifecycle-policy.json:
# {
#   "Rules": [{
#     "Id": "ArchiveOldLogs",
#     "Status": "Enabled",
#     "Transitions": [{
#       "Days": 365,
#       "StorageClass": "GLACIER"
#     }]
#   }]
# }
```

### Backup & Recovery

**DynamoDB Backups:**
```bash
# Enable point-in-time recovery
for table in gka-metadata gka-conversations gka-evaluations gka-audit-trail gka-user-feedback gka-quality-metrics; do
  aws dynamodb update-continuous-backups \
    --table-name $table \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
done

# Create on-demand backup
aws dynamodb create-backup \
  --table-name gka-metadata \
  --backup-name gka-metadata-$(date +%Y%m%d)
```

**S3 Versioning:**
```bash
# Enable versioning (already enabled via Terraform)
aws s3api get-bucket-versioning --bucket $BUCKET

# Restore previous version
aws s3api list-object-versions --bucket $BUCKET --prefix test.txt
aws s3api get-object --bucket $BUCKET --key test.txt --version-id <version-id> restored.txt
```

---

## Performance Tuning

### Query Optimization

**Reduce Latency:**
1. **Enable caching** (already enabled, 1-hour TTL)
2. **Increase Lambda memory** → More CPU power
3. **Use provisioned concurrency** → Eliminate cold starts
4. **Optimize OpenSearch queries** → Reduce search time

**Reduce Cost:**
1. **Use model tiers effectively** → Simple queries use cheaper models
2. **Enable aggressive caching** → Fewer Bedrock calls
3. **Optimize chunk size** → Fewer tokens in context
4. **Use smaller OpenSearch instances** → For dev/test environments

### OpenSearch Tuning

```bash
# Check cluster stats
curl -u $USERNAME:$PASSWORD \
  "https://$OPENSEARCH_ENDPOINT/_cluster/stats?human&pretty"

# Optimize index settings
curl -u $USERNAME:$PASSWORD -X PUT \
  "https://$OPENSEARCH_ENDPOINT/documents/_settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "index": {
      "refresh_interval": "30s",
      "number_of_replicas": 1
    }
  }'

# Force merge (reduce segment count)
curl -u $USERNAME:$PASSWORD -X POST \
  "https://$OPENSEARCH_ENDPOINT/documents/_forcemerge?max_num_segments=1"
```

### Lambda Tuning

```bash
# Analyze Lambda performance
aws lambda get-function-configuration \
  --function-name gka-query-handler | jq .MemorySize,.Timeout

# Increase memory (more CPU)
aws lambda update-function-configuration \
  --function-name gka-query-handler \
  --memory-size 2048

# Increase timeout
aws lambda update-function-configuration \
  --function-name gka-query-handler \
  --timeout 60
```

---

## Security Operations

### Audit Logs Review

```bash
# Query recent audit events
aws dynamodb scan \
  --table-name $AUDIT_TABLE \
  --filter-expression "timestamp > :ts" \
  --expression-attribute-values "{\":ts\":{\"N\":\"$(date -d '24 hours ago' +%s)\"}}" \
  --max-items 100

# Download S3 exports
aws s3 sync s3://$AUDIT_BUCKET/audit-exports/ ./audit-logs/

# Search for specific events
grep "PII_DETECTED" audit-logs/*.json
grep "GUARDRAIL_BLOCKED" audit-logs/*.json
```

### Access Review

```bash
# List IAM roles
aws iam list-roles --query "Roles[?contains(RoleName, 'gka')]"

# Review Lambda execution role
aws iam get-role --role-name gka-lambda-execution-role

# List attached policies
aws iam list-attached-role-policies --role-name gka-lambda-execution-role

# Review policy document
aws iam get-role-policy \
  --role-name gka-lambda-execution-role \
  --policy-name bedrock-access
```

### Rotate Credentials

```bash
# Rotate OpenSearch password
NEW_PASSWORD=$(openssl rand -base64 32)
aws secretsmanager update-secret \
  --secret-id gka-opensearch-credentials \
  --secret-string "{\"username\":\"admin\",\"password\":\"$NEW_PASSWORD\"}"

# Rotate Cognito user passwords (force reset)
aws cognito-idp admin-reset-user-password \
  --user-pool-id $USER_POOL_ID \
  --username user@example.com
```

---

**Last Updated: December 2025**
