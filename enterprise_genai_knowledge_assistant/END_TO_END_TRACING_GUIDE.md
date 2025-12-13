# 🔍 End-to-End Prompt Tracing Guide

## ✅ **Yes, You Can Trace Every Prompt Completely!**

This project has **5 layers of tracing** that let you follow any query from start to finish.

---

## 🎯 **What Gets Tracked**

Every query generates tracking information across:

1. **Request ID** - Unique identifier for the query
2. **CloudWatch Logs** - All processing steps
3. **DynamoDB Audit Trail** - Governance events
4. **DynamoDB Evaluation Table** - Quality metrics
5. **DynamoDB Conversation Table** - Query/response pairs

---

## 📊 **Tracing Architecture**

```
User Query
   │
   ├─ request_id: "abc-123-def"
   │
   ▼
┌─────────────────────────────────────────────────────────┐
│ 1. API Gateway                                          │
│    • API request ID logged                              │
│    • CloudWatch: /aws/apigateway/gka                   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Lambda Query Handler                                 │
│    • request_id = uuid()                                │
│    • CloudWatch: /aws/lambda/gka-query-handler         │
│    • Logs: Query received, PII check, model selection  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Governance Layer (Phase 5)                           │
│    • Audit Trail: DynamoDB gka-audit-trail             │
│    • Logs: PII detection, guardrail checks             │
│    • event_id: uuid() linked to request_id             │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 4. OpenSearch Query                                     │
│    • CloudWatch: OpenSearch logs                        │
│    • Query terms logged                                 │
│    • Results count logged                               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Bedrock Model Invocation                             │
│    • CloudWatch: Bedrock API calls                      │
│    • Model ID logged                                    │
│    • Input/output tokens logged                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Quality Evaluation (Phase 6)                         │
│    • Evaluation Table: DynamoDB gka-quality-evaluation │
│    • 6 quality scores calculated                        │
│    • Linked to request_id                               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Response Storage                                     │
│    • Conversation Table: DynamoDB gka-conversations    │
│    • Query + Response stored                            │
│    • Linked to request_id & conversation_id            │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 **How to Trace a Query (Step-by-Step)**

### **Step 1: Submit a Query and Save the Request ID**

```bash
# Submit query
API_URL="https://your-api-url.amazonaws.com/prod"

RESPONSE=$(curl -X POST "${API_URL}/query" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What is AWS Lambda?",
    "user_id": "test@example.com"
  }')

# Extract request_id
REQUEST_ID=$(echo $RESPONSE | jq -r '.request_id')
echo "Request ID: ${REQUEST_ID}"

# Example output:
# Request ID: 550e8400-e29b-41d4-a716-446655440000
```

---

### **Step 2: Trace Through CloudWatch Logs**

#### **2A. Lambda Query Handler Logs**

```bash
# Search for the request_id in Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-query-handler \
  --filter-pattern "${REQUEST_ID}" \
  --start-time $(date -u -d '10 minutes ago' +%s)000 \
  --end-time $(date -u +%s)000

# You'll see logs like:
# - Query received: "What is AWS Lambda?"
# - PII check: No PII detected
# - Model selected: simple (Claude Instant)
# - OpenSearch query: 10 results found
# - Bedrock invocation: 500 tokens
# - Response generated in 1.2s
# - Quality score: 0.87
```

#### **2B. API Gateway Logs**

```bash
# Search API Gateway logs for the request
aws logs filter-log-events \
  --log-group-name /aws/apigateway/gka \
  --filter-pattern "request" \
  --start-time $(date -u -d '10 minutes ago' +%s)000

# Shows:
# - API request ID
# - HTTP method: POST
# - Path: /query
# - Status code: 200
# - Latency: 1234ms
```

---

### **Step 3: Check Audit Trail (Governance)**

```bash
# Query DynamoDB audit trail
aws dynamodb query \
  --table-name gka-audit-trail \
  --index-name RequestIdIndex \
  --key-condition-expression "request_id = :rid" \
  --expression-attribute-values "{\":rid\": {\"S\": \"${REQUEST_ID}\"}}"

# Returns audit events:
{
  "Items": [
    {
      "id": "audit-001",
      "request_id": "550e8400-...",
      "event_type": "pii_check",
      "timestamp": 1702458000,
      "details": {
        "pii_detected": false,
        "query": "What is AWS Lambda?"
      }
    },
    {
      "id": "audit-002",
      "request_id": "550e8400-...",
      "event_type": "guardrail_check",
      "timestamp": 1702458001,
      "details": {
        "guardrail_id": "gr-abc123",
        "action": "ALLOWED",
        "blocked_content": []
      }
    }
  ]
}
```

---

### **Step 4: Check Quality Evaluation**

```bash
# Query quality evaluation table
aws dynamodb query \
  --table-name gka-quality-evaluation \
  --key-condition-expression "request_id = :rid" \
  --expression-attribute-values "{\":rid\": {\"S\": \"${REQUEST_ID}\"}}"

# Returns quality scores:
{
  "Items": [
    {
      "request_id": "550e8400-...",
      "timestamp": 1702458005,
      "quality_scores": {
        "relevance": 0.92,
        "coherence": 0.85,
        "completeness": 0.88,
        "accuracy": 0.90,
        "conciseness": 0.80,
        "groundedness": 0.87,
        "overall": 0.87
      },
      "query": "What is AWS Lambda?",
      "response": "AWS Lambda is a serverless...",
      "model_id": "anthropic.claude-instant-v1",
      "latency": 1.234,
      "cost": 0.00082
    }
  ]
}
```

---

### **Step 5: Check Conversation History**

```bash
# Query conversation table
aws dynamodb query \
  --table-name gka-conversations \
  --key-condition-expression "conversation_id = :cid" \
  --expression-attribute-values "{\":cid\": {\"S\": \"${CONVERSATION_ID}\"}}"

# Returns all exchanges in the conversation:
{
  "Items": [
    {
      "conversation_id": "conv-123",
      "timestamp": 1702458000,
      "request_id": "550e8400-...",
      "role": "user",
      "content": "What is AWS Lambda?",
      "user_id": "test@example.com"
    },
    {
      "conversation_id": "conv-123",
      "timestamp": 1702458001,
      "request_id": "550e8400-...",
      "role": "assistant",
      "content": "AWS Lambda is a serverless compute service...",
      "model_id": "anthropic.claude-instant-v1",
      "cost": 0.00082
    }
  ]
}
```

---

## 🎯 **Complete Tracing Script**

Save this as `trace_request.sh`:

```bash
#!/bin/bash

# Usage: ./trace_request.sh <request_id>

REQUEST_ID=$1

if [ -z "$REQUEST_ID" ]; then
  echo "Usage: $0 <request_id>"
  exit 1
fi

echo "========================================"
echo "Tracing Request: ${REQUEST_ID}"
echo "========================================"
echo ""

# 1. CloudWatch Logs - Lambda
echo "1. LAMBDA LOGS:"
echo "----------------------------------------"
aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-query-handler \
  --filter-pattern "${REQUEST_ID}" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --query 'events[*].[timestamp, message]' \
  --output table

echo ""
echo ""

# 2. Audit Trail
echo "2. AUDIT TRAIL:"
echo "----------------------------------------"
aws dynamodb query \
  --table-name gka-audit-trail \
  --index-name RequestIdIndex \
  --key-condition-expression "request_id = :rid" \
  --expression-attribute-values "{\":rid\": {\"S\": \"${REQUEST_ID}\"}}" \
  --query 'Items[*].[event_type, timestamp, details]' \
  --output table

echo ""
echo ""

# 3. Quality Evaluation
echo "3. QUALITY EVALUATION:"
echo "----------------------------------------"
aws dynamodb query \
  --table-name gka-quality-evaluation \
  --key-condition-expression "request_id = :rid" \
  --expression-attribute-values "{\":rid\": {\"S\": \"${REQUEST_ID}\"}}" \
  --query 'Items[0].[quality_scores, model_id, latency, cost]' \
  --output table

echo ""
echo ""

# 4. Conversation
echo "4. CONVERSATION DETAILS:"
echo "----------------------------------------"
aws dynamodb scan \
  --table-name gka-conversations \
  --filter-expression "request_id = :rid" \
  --expression-attribute-values "{\":rid\": {\"S\": \"${REQUEST_ID}\"}}" \
  --query 'Items[*].[role, content, timestamp]' \
  --output table

echo ""
echo "========================================"
echo "Trace Complete!"
echo "========================================"
```

**Run it:**
```bash
chmod +x trace_request.sh
./trace_request.sh 550e8400-e29b-41d4-a716-446655440000
```

---

## 📊 **CloudWatch Insights Queries**

### **Query 1: All Steps for a Request**

```sql
fields @timestamp, @message
| filter @message like /550e8400-e29b-41d4-a716-446655440000/
| sort @timestamp asc
```

### **Query 2: Request Flow with Timings**

```sql
fields @timestamp, @message
| filter @message like /request_id/ or @message like /latency/
| parse @message "request_id: * " as req_id
| parse @message "latency: * " as latency
| sort @timestamp asc
```

### **Query 3: Error Tracking**

```sql
fields @timestamp, @message, @logStream
| filter @message like /ERROR/ or @message like /Exception/
| filter @message like /550e8400/
| sort @timestamp desc
```

---

## 🚀 **Enhanced Tracing (Optional - Add AWS X-Ray)**

For **even more detailed tracing**, add AWS X-Ray:

### **Enable X-Ray in API Gateway**

```hcl
# Add to iac/api_gateway.tf

resource "aws_api_gateway_stage" "genai_knowledge_assistant" {
  deployment_id = aws_api_gateway_deployment.genai_knowledge_assistant.id
  rest_api_id   = aws_api_gateway_rest_api.genai_knowledge_assistant.id
  stage_name    = "prod"
  
  # Enable X-Ray tracing
  xray_tracing_enabled = true
}
```

### **Enable X-Ray in Lambda**

```hcl
# Add to iac/lambda.tf

resource "aws_lambda_function" "query_handler" {
  # ... existing config ...
  
  tracing_config {
    mode = "Active"  # Enable X-Ray
  }
}
```

### **Update IAM Policy**

```hcl
# Add to iac/iam.tf

{
  Effect = "Allow"
  Action = [
    "xray:PutTraceSegments",
    "xray:PutTelemetryRecords"
  ]
  Resource = "*"
}
```

### **Add X-Ray to Lambda Code**

```python
# Add to lambda/query_handler/app.py

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch AWS SDK
patch_all()

def handler(event, context):
    # Create subsegment for query processing
    with xray_recorder.in_subsegment('process_query') as subsegment:
        subsegment.put_metadata('request_id', request_id)
        subsegment.put_annotation('query', query)
        
        # Process query...
        
        subsegment.put_metadata('model_selected', model_tier)
```

### **View X-Ray Traces**

```bash
# Get trace for a request
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --filter-expression 'annotation.request_id = "550e8400-..."'

# View in AWS Console
# https://console.aws.amazon.com/xray/home
```

**X-Ray shows:**
- Complete request flow diagram
- Time spent in each service
- Service dependencies
- Errors and exceptions
- Performance bottlenecks

---

## 📈 **Tracing Use Cases**

### **1. Debug Slow Queries**

```bash
# Find slow requests
aws dynamodb scan \
  --table-name gka-quality-evaluation \
  --filter-expression "latency > :threshold" \
  --expression-attribute-values '{":threshold": {"N": "3.0"}}' \
  --projection-expression "request_id, latency, model_id"

# Trace each one
./trace_request.sh <request_id>
```

### **2. Debug Quality Issues**

```bash
# Find low-quality responses
aws dynamodb scan \
  --table-name gka-quality-evaluation \
  --filter-expression "quality_scores.overall < :threshold" \
  --expression-attribute-values '{":threshold": {"N": "0.7"}}' \
  --projection-expression "request_id, quality_scores, query"

# Trace to see what went wrong
./trace_request.sh <request_id>
```

### **3. Audit Compliance**

```bash
# Find all queries with PII
aws dynamodb scan \
  --table-name gka-audit-trail \
  --filter-expression "event_type = :type and details.pii_detected = :val" \
  --expression-attribute-values '{
    ":type": {"S": "pii_check"},
    ":val": {"BOOL": true}
  }' \
  --projection-expression "request_id, timestamp, details"
```

### **4. Cost Analysis**

```bash
# Find expensive queries
aws dynamodb scan \
  --table-name gka-quality-evaluation \
  --filter-expression "cost > :threshold" \
  --expression-attribute-values '{":threshold": {"N": "0.01"}}' \
  --projection-expression "request_id, cost, model_id, query"
```

---

## 🎯 **What You Can Trace**

| Data Point | Where to Find It | How to Query |
|------------|------------------|--------------|
| **Request ID** | Response JSON | Saved when query submitted |
| **Query Text** | CloudWatch Logs | `filter-log-events` with request_id |
| **User ID** | Conversation Table | DynamoDB query |
| **PII Detection** | Audit Trail | DynamoDB query, event_type="pii_check" |
| **Guardrail Checks** | Audit Trail | DynamoDB query, event_type="guardrail_check" |
| **Search Results** | CloudWatch Logs | `filter-log-events` with "OpenSearch" |
| **Model Selected** | Quality Evaluation | DynamoDB query, model_id field |
| **Response Text** | Conversation Table | DynamoDB query |
| **Quality Scores** | Quality Evaluation | DynamoDB query, quality_scores field |
| **Latency** | Quality Evaluation | DynamoDB query, latency field |
| **Cost** | Quality Evaluation | DynamoDB query, cost field |
| **Tokens Used** | CloudWatch Logs | `filter-log-events` with "tokens" |
| **Cache Hit/Miss** | CloudWatch Logs | `filter-log-events` with "cache" |
| **Errors** | CloudWatch Logs | `filter-log-events` with "ERROR" |

---

## 🔧 **Tracing Best Practices**

### **1. Always Save Request IDs**

```bash
# In your client application
response = requests.post(api_url, json=payload)
request_id = response.json()['request_id']

# Log it
logger.info(f"Query submitted, request_id: {request_id}")

# Save to database for later reference
db.save_query_log(user_id, query, request_id)
```

### **2. Use Consistent Timestamps**

All timestamps are in Unix epoch format for easy comparison:

```bash
# Convert to human-readable
date -d @1702458000
# Output: Wed Dec 13 10:00:00 EST 2023
```

### **3. Set Up Alerts for Issues**

```bash
# Alert on high PII detection
aws cloudwatch put-metric-alarm \
  --alarm-name high-pii-detection \
  --alarm-description "Alert when PII detection rate > 5%" \
  --metric-name PIIDetectionRate \
  --namespace GenAI/Governance \
  --statistic Average \
  --period 3600 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

---

## 📊 **Tracing Dashboard**

Create a custom CloudWatch dashboard to visualize traces:

```hcl
# Add to iac/cloudwatch.tf

resource "aws_cloudwatch_dashboard" "tracing" {
  dashboard_name = "gka-tracing"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "log"
        properties = {
          query = """
            fields @timestamp, @message
            | filter @message like /request_id/
            | parse @message "request_id: * " as req_id
            | stats count() by req_id
          """
          region = var.aws_region
          title = "Recent Request IDs"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI", "RequestLatency", {stat = "Average"}],
            [".", "RequestLatency", {stat = "p99"}]
          ]
          view = "timeSeries"
          title = "Request Latency"
        }
      }
    ]
  })
}
```

---

## ✅ **Summary**

**Your project has complete end-to-end tracing!**

✅ **Request IDs** - Unique identifier for every query  
✅ **CloudWatch Logs** - All processing steps logged  
✅ **Audit Trail** - Governance events in DynamoDB  
✅ **Quality Metrics** - Evaluation data in DynamoDB  
✅ **Conversation History** - Query/response pairs stored  

**Optional Enhancements:**
- 🔄 AWS X-Ray for visual tracing
- 🔄 OpenSearch slow query logs
- 🔄 Bedrock API call logging
- 🔄 Custom trace correlation dashboard

**You can trace any query from submission to response in seconds!** 🎉

---

## 🆘 **Quick Reference**

```bash
# 1. Get request_id from response
REQUEST_ID="your-request-id-here"

# 2. Search logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/gka-query-handler \
  --filter-pattern "${REQUEST_ID}"

# 3. Check audit trail
aws dynamodb query \
  --table-name gka-audit-trail \
  --index-name RequestIdIndex \
  --key-condition-expression "request_id = :rid" \
  --expression-attribute-values "{\":rid\": {\"S\": \"${REQUEST_ID}\"}}"

# 4. Check quality
aws dynamodb query \
  --table-name gka-quality-evaluation \
  --key-condition-expression "request_id = :rid" \
  --expression-attribute-values "{\":rid\": {\"S\": \"${REQUEST_ID}\"}}"
```

**Done!** 🚀

