# Quick Start Guide

Get the GenAI Knowledge Assistant up and running in under 30 minutes!

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI configured (`aws configure`)
- [ ] Terraform 1.0+ installed
- [ ] Python 3.10 installed
- [ ] Amazon Bedrock models enabled (see below)

## Step 1: Enable Bedrock Models (5 minutes)

1. Go to [AWS Console → Amazon Bedrock](https://console.aws.amazon.com/bedrock)
2. Click **Model access** in the left sidebar
3. Click **Manage model access**
4. Enable these models:
   - ✅ Amazon Titan Embeddings G1 - Text
   - ✅ Claude 3 Sonnet
5. Click **Save changes**

## Step 2: Configure Deployment (2 minutes)

```bash
# Navigate to project directory
cd enterprise_genai_knowledge_assistant/iac

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your settings (optional - defaults work fine)
nano terraform.tfvars
```

## Step 3: Deploy Infrastructure (15-20 minutes)

### Option A: Automated Deployment (Recommended)

```bash
# From the project root
./deploy.sh
```

### Option B: Manual Deployment

```bash
cd iac

# Initialize Terraform
terraform init

# Review deployment plan
terraform plan

# Deploy infrastructure
terraform apply
```

## Step 4: Initialize OpenSearch Index (2 minutes)

```bash
# Get deployment outputs
cd iac
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
SECRET_NAME=$(terraform output -raw opensearch_password_secret_arn | awk -F: '{print $NF}')

# Get credentials
CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id $SECRET_NAME --query SecretString --output text)
USERNAME=$(echo $CREDENTIALS | jq -r .username)
PASSWORD=$(echo $CREDENTIALS | jq -r .password)

# Create index
curl -X PUT "https://$OPENSEARCH_ENDPOINT/documents" \
  -u "$USERNAME:$PASSWORD" \
  -H 'Content-Type: application/json' \
  -d '{
    "mappings": {
      "properties": {
        "content": { "type": "text" },
        "embedding": { "type": "knn_vector", "dimension": 1536 },
        "metadata": { "type": "object" }
      }
    },
    "settings": { "index": { "knn": true } }
  }'
```

## Step 5: Test Your Deployment (5 minutes)

### Get API URL

```bash
API_URL=$(terraform output -raw api_gateway_url)
echo "Your API URL: $API_URL"
```

### Upload a Test Document

```bash
curl -X POST "$API_URL/documents" \
  -H 'Content-Type: application/json' \
  -d '{
    "document_id": "doc-001",
    "content": "Amazon Web Services (AWS) is a comprehensive cloud computing platform. AWS Lambda is a serverless compute service that lets you run code without provisioning servers. Amazon S3 is object storage built to store and retrieve any amount of data.",
    "metadata": {
      "title": "AWS Overview",
      "category": "Cloud Computing",
      "source": "AWS Documentation"
    }
  }'
```

Expected response:
```json
{
  "status": "success",
  "document_id": "doc-001",
  "message": "Document processed successfully"
}
```

### Ask a Question

```bash
curl -X POST "$API_URL/query" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What is AWS Lambda?",
    "max_results": 3
  }'
```

Expected response:
```json
{
  "answer": "AWS Lambda is a serverless compute service...",
  "sources": [
    {
      "document_id": "doc-001",
      "relevance_score": 0.95,
      "excerpt": "AWS Lambda is a serverless compute service..."
    }
  ],
  "conversation_id": "conv-1234567890"
}
```

## Step 6: View Monitoring Dashboard

1. Go to [AWS Console → CloudWatch](https://console.aws.amazon.com/cloudwatch)
2. Click **Dashboards** in the left sidebar
3. Select `genai-knowledge-assistant-dev`
4. View real-time metrics for your deployment

## Architecture Overview

```
┌─────────────┐
│   API GW    │ ← Your API endpoint
└──────┬──────┘
       │
       ├─────────────┬─────────────┐
       │             │             │
   ┌───▼────┐   ┌───▼────┐   ┌───▼────┐
   │Document│   │ Query  │   │DynamoDB│
   │Processor   │Handler │   │        │
   └───┬────┘   └───┬────┘   └────────┘
       │            │
   ┌───▼────────────▼────┐
   │   OpenSearch         │ ← Vector search
   │   (with KNN)         │
   └──────────────────────┘
          │
   ┌──────▼──────┐
   │   Bedrock   │ ← AI models
   │(Embeddings  │
   │ + Claude)   │
   └─────────────┘
```

## Common Commands

### View Deployment Info
```bash
cd iac
terraform output
```

### View Logs
```bash
# Document processor logs
aws logs tail /aws/lambda/genai-knowledge-assistant-document-processor-dev --follow

# Query handler logs
aws logs tail /aws/lambda/genai-knowledge-assistant-query-handler-dev --follow
```

### Update Infrastructure
```bash
cd iac
terraform plan
terraform apply
```

### Destroy Everything
```bash
cd iac
terraform destroy
```

## Troubleshooting

### Issue: OpenSearch domain creation takes too long
**Solution**: This is normal. First-time creation takes 15-20 minutes. Wait patiently.

### Issue: Lambda timeout errors
**Solution**: Increase timeout in `terraform.tfvars`:
```hcl
document_processor_timeout = 300
lambda_timeout = 120
```

### Issue: "Access Denied" to Bedrock
**Solution**: 
1. Verify model access in Bedrock console
2. Check your AWS region supports Bedrock
3. Ensure IAM permissions are correct

### Issue: API Gateway returns 403
**Solution**: Redeploy API Gateway:
```bash
terraform taint aws_api_gateway_deployment.genai_knowledge_assistant
terraform apply
```

## Cost Estimate

Based on moderate usage (dev environment):

| Service | Estimated Monthly Cost |
|---------|----------------------|
| OpenSearch (2x r6g.large) | $250 |
| Lambda (10K invocations) | $2 |
| API Gateway (10K requests) | $0.04 |
| DynamoDB (on-demand) | $1-5 |
| S3 Storage (10GB) | $0.23 |
| CloudWatch Logs | $1-3 |
| **Total** | **~$255/month** |

To reduce costs:
- Use smaller OpenSearch instances (`t3.small.search`)
- Implement API caching
- Set up S3 lifecycle policies

## Next Steps

1. **Add More Documents**: Upload your knowledge base
2. **Configure Authentication**: Add Cognito or API keys
3. **Set Up Alerts**: Configure SNS notifications for alarms
4. **Custom Domain**: Add Route53 and ACM certificate
5. **Production Hardening**: Review security best practices

## Getting Help

- 📖 Full documentation: [README.md](README.md)
- 🚀 Detailed deployment: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- 🔄 CDK conversion details: [CDK_TO_TERRAFORM_CONVERSION.md](CDK_TO_TERRAFORM_CONVERSION.md)

## Success Checklist

- [ ] Infrastructure deployed successfully
- [ ] OpenSearch index created
- [ ] Test document uploaded
- [ ] Test query returned results
- [ ] CloudWatch dashboard accessible
- [ ] No errors in Lambda logs

🎉 **Congratulations!** Your GenAI Knowledge Assistant is running!

## Example Use Cases

### Customer Support Knowledge Base
Upload support articles, FAQs, and documentation. Users can ask questions in natural language.

### Internal Company Wiki
Index company policies, procedures, and documents. Employees get instant answers.

### Product Documentation Search
Semantic search across product docs, API references, and guides.

### Research Assistant
Upload research papers and articles. Ask questions to get relevant information.

## API Examples

### Upload Multiple Documents
```bash
for i in {1..5}; do
  curl -X POST "$API_URL/documents" \
    -H 'Content-Type: application/json' \
    -d "{
      \"document_id\": \"doc-$i\",
      \"content\": \"Document content $i...\",
      \"metadata\": {\"title\": \"Document $i\"}
    }"
done
```

### Conversational Query
```bash
# First query
curl -X POST "$API_URL/query" \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is AWS?"}' | jq -r '.conversation_id' > conv_id.txt

# Follow-up query with context
curl -X POST "$API_URL/query" \
  -H 'Content-Type: application/json' \
  -d "{
    \"query\": \"Tell me more about Lambda\",
    \"conversation_id\": \"$(cat conv_id.txt)\"
  }"
```

Happy building! 🚀

