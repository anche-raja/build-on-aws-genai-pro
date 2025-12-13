# Deployment Guide

## Step-by-Step Deployment Instructions

### Prerequisites Checklist

- [ ] AWS Account with administrative access
- [ ] AWS CLI installed and configured
- [ ] Terraform >= 1.0 installed
- [ ] Python >= 3.11 installed
- [ ] Bedrock model access enabled

### Step 1: Enable Amazon Bedrock Model Access

1. **Navigate to Amazon Bedrock Console**
   ```
   https://console.aws.amazon.com/bedrock/
   ```

2. **Go to Model Access**
   - Click on "Model access" in the left navigation
   - Click "Modify model access"

3. **Select Required Models**
   - ✅ Amazon Titan Embeddings G1 - Text
   - ✅ Anthropic Claude 3 Sonnet
   - ✅ Anthropic Claude 3 Haiku (optional)
   - ✅ Anthropic Claude 3 Opus (optional)

4. **Submit Request**
   - Click "Request model access"
   - Wait for approval (usually instant)

### Step 2: Clone and Prepare Project

```bash
# Navigate to project
cd /path/to/build-on-aws-genai-pro/01_1.4_rag_vector_search_system

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify credentials
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/YourUser"
}
```

### Step 4: Configure Infrastructure Variables

```bash
# Copy example configuration
cp iac/terraform.tfvars.example iac/terraform.tfvars

# Edit with your settings
nano iac/terraform.tfvars
```

**Required Changes**:
```hcl
# IMPORTANT: Must be globally unique!
document_bucket_name = "rag-docs-yourname-20241204"

# Your AWS region
aws_region = "us-east-1"

# Environment name
environment = "dev"
```

**Optional Optimizations**:

For **Production**:
```hcl
environment                = "prod"
opensearch_instance_type   = "r6g.xlarge.search"
opensearch_instance_count  = 3
opensearch_ebs_volume_size = 200
lambda_memory_size         = 2048
```

For **Development/Testing**:
```hcl
environment                = "dev"
opensearch_instance_type   = "t3.medium.search"
opensearch_instance_count  = 1
opensearch_ebs_volume_size = 50
lambda_memory_size         = 512
```

### Step 5: Deploy Infrastructure

#### Option A: Automated Deployment (Recommended)

```bash
# Make script executable
chmod +x setup_infrastructure.sh

# Run deployment
./setup_infrastructure.sh
```

The script will:
1. ✅ Verify prerequisites
2. ✅ Package Lambda functions
3. ✅ Initialize Terraform
4. ✅ Create infrastructure plan
5. ✅ Prompt for confirmation
6. ✅ Deploy all resources
7. ✅ Display outputs

#### Option B: Manual Deployment

```bash
# 1. Package Lambda functions
cd app
zip -r ../lambda_document_processor.zip .
cd ..
zip -g lambda_document_processor.zip lambda_document_processor.py

cd app
zip -r ../lambda_sync_scheduler.zip .
cd ..
zip -g lambda_sync_scheduler.zip lambda_sync_scheduler.py

cd app
zip -r ../lambda_rag_api.zip .
cd ..
zip -g lambda_rag_api.zip lambda_rag_api.py

# 2. Initialize Terraform
cd iac
terraform init

# 3. Review plan
terraform plan -out=tfplan

# 4. Apply configuration
terraform apply tfplan

# 5. Save outputs
terraform output > ../deployment_outputs.txt
```

### Step 6: Verify Deployment

```bash
# Get important outputs
cd iac

# S3 Bucket
terraform output s3_bucket_name

# OpenSearch Endpoint
terraform output opensearch_endpoint

# API Gateway URL
terraform output api_gateway_url

# Verify resources exist
aws s3 ls $(terraform output -raw s3_bucket_name)
aws dynamodb describe-table --table-name DocumentMetadata
aws lambda list-functions --query 'Functions[?contains(FunctionName, `rag`)].FunctionName'
```

### Step 7: Upload Sample Documents

```bash
# Export bucket name
export BUCKET_NAME=$(cd iac && terraform output -raw s3_bucket_name)

# Upload test documents
aws s3 cp sample-data/sample_doc1.txt s3://$BUCKET_NAME/documents/
aws s3 cp sample-data/sample_doc2.txt s3://$BUCKET_NAME/documents/

# Verify upload
aws s3 ls s3://$BUCKET_NAME/documents/
```

### Step 8: Monitor Processing

```bash
# Check Lambda logs
aws logs tail /aws/lambda/rag-vector-search-document-processor --follow

# Check DynamoDB for metadata
aws dynamodb scan \
  --table-name DocumentMetadata \
  --select COUNT

# Query OpenSearch (requires credentials from Secrets Manager)
export OS_ENDPOINT=$(cd iac && terraform output -raw opensearch_endpoint)
```

### Step 9: Test the API

```bash
# Get API endpoint
export API_URL=$(cd iac && terraform output -raw api_gateway_url)

# Test query
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Amazon Bedrock?",
    "num_results": 3
  }' | jq '.'
```

Expected response:
```json
{
  "answer": "Amazon Bedrock is a fully managed service...",
  "sources": [
    {
      "text": "Amazon Bedrock Overview...",
      "score": 0.85,
      "metadata": {...}
    }
  ],
  "metadata": {
    "query": "What is Amazon Bedrock?",
    "num_sources": 3,
    "processing_time_ms": 1234.56
  }
}
```

### Step 10: Set Up Monitoring (Optional)

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name rag-vector-search-dashboard \
  --dashboard-body file://cloudwatch_dashboard.json

# Set up alarms for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name rag-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

## Post-Deployment Tasks

### 1. Security Hardening

```bash
# Enable MFA for OpenSearch
aws opensearch update-domain-config \
  --domain-name rag-vector-search-domain \
  --advanced-security-options MasterUserOptions={MFAEnabled=true}

# Add API Gateway authorizer (for production)
# Update iac/api_gateway.tf with AWS Cognito or Lambda authorizer
```

### 2. Enable Auto-Scaling (Production)

```bash
# Configure OpenSearch auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace es \
  --resource-id domain/rag-vector-search-domain \
  --scalable-dimension es:domain:DesiredInstanceCount \
  --min-capacity 3 \
  --max-capacity 10
```

### 3. Set Up Backup Schedule

```bash
# Enable automated snapshots (included in terraform)
# Configure retention in OpenSearch console

# Enable DynamoDB backups (Point-in-time recovery already enabled)
aws dynamodb update-continuous-backups \
  --table-name DocumentMetadata \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### 4. Configure Custom Domain (Optional)

```bash
# Create certificate in ACM
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS

# Add custom domain to API Gateway
# Update Route53 or your DNS provider
```

## Troubleshooting Deployment

### Issue: Terraform apply fails with "bucket name already exists"

**Solution**: Change `document_bucket_name` to a globally unique value

```hcl
document_bucket_name = "rag-docs-yourname-$(date +%s)"
```

### Issue: OpenSearch domain creation fails

**Solution**: Check service limits
```bash
aws service-quotas get-service-quota \
  --service-code es \
  --quota-code L-BC0C137F
```

### Issue: Lambda deployment package too large

**Solution**: Use Lambda layers
```bash
# Create layer with dependencies
pip install -r requirements.txt -t python/lib/python3.11/site-packages/
zip -r dependencies-layer.zip python/
aws lambda publish-layer-version \
  --layer-name rag-dependencies \
  --zip-file fileb://dependencies-layer.zip \
  --compatible-runtimes python3.11
```

### Issue: Bedrock model access denied

**Solution**: Wait for model access approval and verify:
```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `titan-embed`)]'
```

## Cleanup / Destroy Resources

⚠️ **WARNING**: This will delete all resources and data!

```bash
# Option 1: Automated cleanup
cd iac
terraform destroy

# Option 2: Manual cleanup (safer for production)
# 1. Empty S3 bucket first
aws s3 rm s3://$BUCKET_NAME --recursive

# 2. Delete OpenSearch domain (takes ~15 minutes)
aws opensearch delete-domain --domain-name rag-vector-search-domain

# 3. Run terraform destroy
terraform destroy
```

## Deployment Checklist

### Pre-Deployment
- [ ] AWS credentials configured
- [ ] Bedrock model access enabled
- [ ] Terraform installed
- [ ] Python dependencies installed
- [ ] Unique S3 bucket name chosen
- [ ] terraform.tfvars configured

### During Deployment
- [ ] Terraform init successful
- [ ] Terraform plan reviewed
- [ ] Terraform apply completed
- [ ] No error messages in outputs

### Post-Deployment
- [ ] S3 bucket created
- [ ] DynamoDB tables exist
- [ ] OpenSearch domain healthy
- [ ] Lambda functions deployed
- [ ] API Gateway endpoint accessible
- [ ] Sample documents uploaded
- [ ] Test query successful

### Production Readiness
- [ ] VPC deployment configured
- [ ] API authentication added
- [ ] CloudWatch alarms set up
- [ ] Backup schedules configured
- [ ] Auto-scaling enabled
- [ ] Custom domain configured
- [ ] Security review completed
- [ ] Cost alerts configured

## Next Steps

1. **Upload Your Documents**: Add your documentation to the S3 bucket
2. **Configure Integrations**: Set up web crawlers or wiki connectors
3. **Customize Prompts**: Adjust system prompts in `rag_application.py`
4. **Build Frontend**: Create a web UI using AWS Amplify
5. **Monitor Usage**: Set up dashboards and alerts
6. **Iterate**: Collect feedback and improve based on user queries

---

**Need Help?** Check the [README.md](README.md) for additional resources and troubleshooting tips.





