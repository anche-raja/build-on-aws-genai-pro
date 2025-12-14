# Enterprise GenAI Knowledge Assistant

Production-ready enterprise knowledge assistant built with Amazon Bedrock, OpenSearch, and AWS serverless technologies. Features intelligent RAG, multi-tier model selection, content safety guardrails, and comprehensive monitoring.

---

## ✨ Features

- 🔍 **Intelligent RAG** - Hybrid search (vector + keyword) with semantic retrieval
- 🤖 **Multi-Tier Models** - Dynamic model selection (Simple/Standard/Advanced) based on query complexity
- 🛡️ **Content Safety** - PII detection, redaction, and Bedrock guardrails
- 📊 **Monitoring & Analytics** - Quality metrics, user feedback, and performance tracking
- 🔐 **Governance & Compliance** - Comprehensive audit trails and compliance reporting
- 💬 **Web Interface** - Modern React UI with real-time chat and document upload
- 📈 **Cost Optimization** - Smart caching and intelligent model tier selection

---

## 🚀 Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0
- Python 3.10+
- Node.js 18+ (for web interface)
- AWS CLI configured
- Amazon Bedrock model access enabled (Claude, Titan)

### 1. Enable Bedrock Models

```bash
# Go to AWS Console → Amazon Bedrock → Model access
# Enable: Claude 3 Sonnet, Claude 2.1, Claude Instant, Titan Embeddings
```

### 2. Deploy Infrastructure

```bash
cd iac
terraform init
terraform apply
```

**Deployment time:** ~20-30 minutes (OpenSearch takes longest)

**Resources created:**
- 5 Lambda functions (document processor, query handler, 3 scheduled tasks)
- OpenSearch domain for vector search
- 6 DynamoDB tables (metadata, conversations, evaluations, audit trail, feedback, quality metrics)
- 3 S3 buckets (documents, audit logs, analytics exports)
- API Gateway REST API
- Bedrock guardrails and SNS alerts
- CloudWatch dashboards and alarms
- Cognito user pool and identity pool
- CloudFront distribution (web app CDN)

### 3. Build and Deploy Lambda Functions

```bash
# From project root
./build-lambda.sh

# Deploy via Terraform
cd iac
terraform apply

# OR update individual functions via AWS CLI
cd lambda/<function-name>/package
zip -r ../deploy.zip .
aws lambda update-function-code \
  --function-name gka-<function-name> \
  --zip-file fileb://../deploy.zip
```

### 4. Deploy Web Interface

```bash
# Get Terraform outputs
cd iac
terraform output

# Update web app configuration
cd ../web
# Edit src/aws-exports.js with Cognito and API Gateway URLs

# Install and build
npm install
npm run build

# Deploy (Option A: using provided script)
./update-and-deploy.sh

# Deploy (Option B: to S3+CloudFront)
aws s3 sync build/ s3://gka-amplify-deployment-<account-id>/
```

### 5. Create Users and Test

```bash
# Create Cognito user
USER_POOL_ID=$(cd iac && terraform output -raw cognito_user_pool_id)
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com

# Get web app URL
WEB_URL=$(cd iac && terraform output -raw web_app_url)
echo "Web App: $WEB_URL"

# Open and test
# 1. Sign up / Log in
# 2. Upload a test document
# 3. Wait for processing (~10-30 seconds)
# 4. Query the knowledge base
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Complete system architecture, data flows, components, and cost breakdown |
| **[DEPLOYMENT.md](./DEPLOYMENT.md)** | Detailed deployment guide with step-by-step instructions |
| **[OPERATIONS.md](./OPERATIONS.md)** | Monitoring, testing, troubleshooting, and maintenance guide |

---

## 🏗️ Architecture Overview

```
Web App (React + Cognito) 
    ↓
API Gateway + CloudFront
    ↓
Lambda Functions (5)
    ├─ document_processor → S3 → Chunking → Embeddings → OpenSearch
    ├─ query_handler → Guardrails → PII Detection → RAG → Bedrock → Cache
    ├─ quality_reporter → Daily quality reports → S3
    ├─ analytics_exporter → Weekly analytics → S3
    └─ audit_exporter → Daily audit archival → S3
    ↓
Storage Layer
    ├─ OpenSearch (vector search)
    ├─ DynamoDB (6 tables)
    └─ S3 (3 buckets)
    ↓
Monitoring Layer
    ├─ CloudWatch (logs, metrics, dashboards, alarms)
    └─ SNS (alerts)
```

**See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed diagrams and flows.**

---

## 💻 Usage

### Upload Documents

**Via Web UI:**
```
Open web app → Document Upload → Select file → Upload
```

**Via API:**
```bash
API_URL=$(cd iac && terraform output -raw api_gateway_url)

curl -X POST ${API_URL}/documents \
  -H "Content-Type: application/json" \
  -d '{
    "document_key": "my-document.pdf",
    "document_type": "application/pdf",
    "metadata": {
      "title": "My Document",
      "author": "John Doe"
    }
  }'
```

### Query the Knowledge Base

**Via Web UI:**
```
Open web app → Chat → Type question → Submit
```

**Via API:**
```bash
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the refund policy?",
    "conversation_id": "conv-123"
  }'
```

### Submit Feedback

**Via Web UI:**
```
After query response → Click thumbs up/down → Add comment → Submit
```

**Via API:**
```bash
curl -X POST ${API_URL}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "query-123",
    "rating": 5,
    "thumbs": "up",
    "comment": "Great response!"
  }'
```

---

## 🔧 Configuration

### Environment Variables

Lambda functions use these environment variables (set automatically by Terraform):

```bash
OPENSEARCH_DOMAIN              # OpenSearch endpoint
METADATA_TABLE                 # DynamoDB table for document metadata
CONVERSATION_TABLE             # DynamoDB table for conversations
EVALUATION_TABLE               # DynamoDB table for quality evaluations
AUDIT_TRAIL_TABLE              # DynamoDB table for audit logs
USER_FEEDBACK_TABLE            # DynamoDB table for user feedback
QUALITY_METRICS_TABLE          # DynamoDB table for quality metrics
DOCUMENT_BUCKET                # S3 bucket for documents
AUDIT_LOGS_BUCKET              # S3 bucket for audit archives
ANALYTICS_EXPORTS_BUCKET       # S3 bucket for analytics exports
GUARDRAIL_ID                   # Bedrock guardrail identifier
GUARDRAIL_VERSION              # Bedrock guardrail version
COMPLIANCE_ALERTS_TOPIC        # SNS topic for compliance alerts
QUALITY_ALERTS_TOPIC           # SNS topic for quality alerts
OPENSEARCH_SECRET_ARN          # Secrets Manager ARN for OpenSearch creds
```

### Model Configuration

Edit model tiers in `lambda/query_handler/app.py`:

```python
# Model tier configuration
SIMPLE_MODEL = "amazon.titan-text-lite-v1"
STANDARD_MODEL = "anthropic.claude-v2:1"
ADVANCED_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"

# Model selection thresholds
SIMPLE_THRESHOLD = 50    # Complexity score < 50 → Simple
STANDARD_THRESHOLD = 75  # 50 <= score < 75 → Standard
                         # score >= 75 → Advanced
```

### Caching Configuration

```python
# Cache TTL in seconds (default: 1 hour)
CACHE_TTL = 3600

# Disable caching
ENABLE_CACHE = False
```

---

## 📊 Monitoring

### CloudWatch Dashboards

```bash
# Main dashboard
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=gka"

# Governance dashboard
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=gka-governance"

# Quality dashboard
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=gka-quality"
```

### Lambda Logs

```bash
# Query handler logs
aws logs tail /aws/lambda/gka-query-handler --follow

# Document processor logs
aws logs tail /aws/lambda/gka-document-processor --follow

# All Lambda errors
aws logs tail /aws/lambda/gka-* --follow --filter-pattern "ERROR"
```

### Metrics

**Key Metrics (CloudWatch):**
- Query latency, cost, complexity
- Model tier usage
- Cache hit rate
- Quality scores
- PII detections
- Guardrail blocks

**See [OPERATIONS.md](./OPERATIONS.md) for detailed monitoring guide.**

---

## 💰 Cost Estimate

**Monthly costs (moderate usage):**

| Service | Cost |
|---------|------|
| Lambda (100K invocations) | $20-30 |
| OpenSearch (2x r6g.large.search) | $250 |
| DynamoDB (pay-per-request) | $5-10 |
| S3 (storage + requests) | $5 |
| Bedrock (usage-based) | $50-200 |
| CloudWatch | $10-15 |
| API Gateway | $3.50 |
| Other (Cognito, SNS, CloudFront) | $5 |
| **Total** | **$349-519/month** |

**Cost optimization:**
- Use `t3.small.search` for dev/test ($40/mo vs $250/mo)
- Enable caching (reduces Bedrock calls by ~40%)
- Use model tiering (saves ~30% on inference)

**See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed cost breakdown.**

---

## 🛠️ Troubleshooting

### Document Upload Fails (502 Error)

```bash
# Check Lambda logs
aws logs tail /aws/lambda/gka-document-processor --follow

# Rebuild and redeploy
./build-lambda.sh
cd iac && terraform apply
```

### Query Returns Empty Results

```bash
# Check if documents are indexed
OPENSEARCH_ENDPOINT=$(cd iac && terraform output -raw opensearch_endpoint)
curl -u admin:password "https://$OPENSEARCH_ENDPOINT/documents/_count"

# Check metadata table
aws dynamodb scan --table-name gka-metadata --max-items 5
```

### High Latency

```bash
# Check metrics
aws cloudwatch get-metric-statistics \
  --namespace GenAI/KnowledgeAssistant \
  --metric-name QueryLatency \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Increase Lambda memory
aws lambda update-function-configuration \
  --function-name gka-query-handler \
  --memory-size 2048
```

**See [OPERATIONS.md](./OPERATIONS.md) for comprehensive troubleshooting guide.**

---

## 🔒 Security

- ✅ **Encryption**: At-rest (S3, DynamoDB, OpenSearch) and in-transit (TLS 1.2+)
- ✅ **PII Detection**: Automatic detection and redaction (AWS Comprehend)
- ✅ **Content Filtering**: Bedrock guardrails for harmful content
- ✅ **Access Control**: IAM roles with least privilege, Cognito authentication
- ✅ **Audit Logging**: 7-year retention for compliance (SOC 2, HIPAA, GDPR ready)
- ✅ **Secrets Management**: AWS Secrets Manager for credentials

---

## 📦 Project Structure

```
enterprise_genai_knowledge_assistant/
├── iac/                        # Terraform infrastructure code
│   ├── provider.tf             # AWS provider configuration
│   ├── variables.tf            # Input variables
│   ├── lambda.tf               # Lambda functions
│   ├── opensearch.tf           # OpenSearch domain
│   ├── dynamodb.tf             # DynamoDB tables
│   ├── s3.tf                   # S3 buckets
│   ├── api_gateway.tf          # API Gateway
│   ├── amplify_cognito.tf      # Cognito user pool, identity pool
│   ├── bedrock_guardrails.tf   # Content safety guardrails
│   ├── monitoring_evaluation.tf # CloudWatch, SNS, EventBridge
│   ├── governance_dashboard.tf # Governance dashboard
│   ├── cloudwatch.tf           # Main dashboard
│   ├── iam.tf                  # IAM roles and policies
│   └── outputs.tf              # Output values
├── lambda/                     # Lambda function code
│   ├── document_processor/     # Document processing
│   ├── query_handler/          # Query processing & RAG
│   ├── quality_reporter/       # Daily quality reports
│   ├── analytics_exporter/     # Weekly analytics export
│   ├── audit_exporter/         # Daily audit archival
│   └── shared/                 # Shared utilities
├── web/                        # React web interface
│   ├── src/
│   │   ├── pages/              # Chat, DocumentUpload, Analytics, etc.
│   │   ├── components/         # Reusable React components
│   │   └── aws-exports.js      # AWS configuration
│   ├── public/
│   └── package.json
├── build-lambda.sh             # Lambda build script
├── README.md                   # This file
├── ARCHITECTURE.md             # Complete architecture guide
├── DEPLOYMENT.md               # Detailed deployment guide
└── OPERATIONS.md               # Monitoring and operations guide
```

---

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test locally
4. Update documentation
5. Submit pull request

---

## 📄 License

This project is for enterprise use. See your organization's license policy.

---

## 🆘 Support

For issues or questions:

1. **Check documentation**: ARCHITECTURE.md, DEPLOYMENT.md, OPERATIONS.md
2. **Review logs**: CloudWatch Logs for Lambda functions
3. **Check dashboards**: CloudWatch dashboards for metrics
4. **Verify resources**: Terraform outputs and AWS Console

---

## 📈 Version

**Current Version:** 1.0.0  
**Last Updated:** December 2025

---

**Built with ❤️ using AWS Serverless Technologies**
