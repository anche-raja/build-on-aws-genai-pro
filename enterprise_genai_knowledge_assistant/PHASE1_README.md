# Phase 1: Core Infrastructure - README

## 🎯 **Quick Start**

Deploy the core infrastructure for the GenAI Knowledge Assistant.

### **Prerequisites:**
```bash
- AWS Account with appropriate permissions
- Terraform >= 1.0
- AWS CLI >= 2.0 configured
- ~$280/month budget for infrastructure
```

### **Deploy:**
```bash
cd enterprise_genai_knowledge_assistant/iac

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Deploy (takes ~15 minutes for OpenSearch)
terraform apply

# Get outputs
terraform output
```

---

## 📋 **What Gets Created**

### **API Layer:**
- ✅ API Gateway REST API with 3 endpoints
- ✅ CloudWatch logging enabled
- ✅ CORS configured

### **Compute Layer:**
- ✅ 2 Lambda functions (Document Processor, Query Handler)
- ✅ Python 3.10 runtime
- ✅ Proper IAM roles and permissions

### **Storage Layer:**
- ✅ S3 bucket for documents (encrypted, versioned)
- ✅ OpenSearch domain (2x r6g.large.search)
- ✅ 3 DynamoDB tables (metadata, conversations, evaluation)

### **Security Layer:**
- ✅ IAM roles with least privilege
- ✅ Secrets Manager for OpenSearch credentials
- ✅ VPC for OpenSearch isolation

### **Monitoring Layer:**
- ✅ CloudWatch log groups (14-day retention)
- ✅ CloudWatch dashboard
- ✅ CloudWatch alarms for errors and performance

---

## 🔧 **Configuration**

### **Variables:**

Edit `iac/variables.tf` or create `terraform.tfvars`:

```hcl
# Required
aws_region   = "us-east-1"
project_name = "gka"

# Optional (has defaults)
opensearch_instance_type = "r6g.large.search"
opensearch_instance_count = 2
lambda_memory_size = 512
```

### **Cost Optimization:**

For development/testing:
```hcl
# Use smaller OpenSearch instances
opensearch_instance_type = "t3.small.search"
opensearch_instance_count = 1
opensearch_dedicated_master_enabled = false

# Reduce Lambda memory
lambda_memory_size = 256
```

**Dev Cost:** ~$40/month (vs $280/month prod)

---

## 📊 **Outputs**

After deployment, get important values:

```bash
# API URL
terraform output api_url
# Example: https://abc123.execute-api.us-east-1.amazonaws.com/prod

# S3 Bucket
terraform output s3_bucket_name
# Example: gka-documents-123456789

# OpenSearch Endpoint
terraform output opensearch_endpoint
# Example: vpc-gka-vector-search-abc.us-east-1.es.amazonaws.com

# DynamoDB Tables
terraform output dynamodb_tables
# Example: {metadata = "gka-metadata", ...}
```

Save these for later use!

---

## 🧪 **Testing**

### **Test 1: API Gateway Accessibility**

```bash
API_URL=$(terraform output -raw api_url)

# Test API is accessible
curl "${API_URL}/documents" \
  -X OPTIONS \
  -H "Origin: http://localhost:3000"

# Should return CORS headers
```

### **Test 2: Lambda Functions**

```bash
# Invoke document processor directly
aws lambda invoke \
  --function-name gka-document-processor \
  --payload '{"test": true}' \
  response.json

# Check response
cat response.json
```

### **Test 3: OpenSearch Cluster**

```bash
# Get OpenSearch endpoint
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)

# Check cluster health (requires VPN/bastion if in VPC)
curl -u admin:password "https://${OPENSEARCH_ENDPOINT}/_cluster/health"

# Expected: {"status": "green" or "yellow"}
```

### **Test 4: DynamoDB Tables**

```bash
# List items in metadata table
aws dynamodb scan \
  --table-name gka-metadata \
  --max-items 10
```

### **Test 5: CloudWatch Logs**

```bash
# Check Lambda logs
aws logs tail /aws/lambda/gka-document-processor --follow

# Check API Gateway logs
aws logs tail /aws/apigateway/gka --follow
```

---

## 📈 **Monitoring**

### **CloudWatch Dashboard**

Access the dashboard:
```bash
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=gka"
```

**Widgets:**
- Lambda invocations, errors, duration
- API Gateway requests, latency, errors
- OpenSearch CPU, memory, search latency
- DynamoDB read/write capacity

### **CloudWatch Alarms**

```bash
# List all alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix gka

# Check alarm status
aws cloudwatch describe-alarm-history \
  --alarm-name gka-lambda-errors
```

### **Log Insights Queries**

```sql
-- Lambda errors
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20

-- API Gateway 5xx errors
fields @timestamp, status, request_id
| filter status >= 500
| stats count() by bin(5m)

-- Slow Lambda executions
fields @timestamp, @duration
| filter @duration > 3000
| sort @duration desc
```

---

## 💰 **Cost Breakdown**

### **Monthly Costs (Production):**

```
OpenSearch (2x r6g.large): $250
Lambda (100K invocations):  $20
DynamoDB (on-demand):       $5
API Gateway (100K req):     $3.50
S3 (10 GB + requests):      $0.25
CloudWatch (logs+metrics):  $2
Secrets Manager:            $0.40
Data Transfer:              $1
──────────────────────────────
Total:                      $282/month
```

### **Daily Costs:**
- ~$9.40 per day
- ~$0.39 per hour

### **Per-Query Cost:**
- $0.00282 (infrastructure only)
- Does not include Bedrock costs (added in Phase 4)

### **Cost Monitoring:**

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '1 month ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Set up budget alert
aws budgets create-budget \
  --account-id 123456789 \
  --budget '{
    "BudgetName": "gka-monthly-budget",
    "BudgetLimit": {"Amount": "300", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }'
```

---

## 🔒 **Security Best Practices**

### **Implemented:**
- ✅ All data encrypted at rest (S3, DynamoDB, OpenSearch)
- ✅ All data encrypted in transit (TLS 1.2+)
- ✅ IAM roles with least privilege
- ✅ Secrets Manager for credentials
- ✅ VPC isolation for OpenSearch
- ✅ Public access blocked on S3
- ✅ CloudWatch logging enabled

### **Recommended:**

```bash
# 1. Enable AWS WAF on API Gateway
# Protects against common web exploits

# 2. Enable GuardDuty
aws guardduty create-detector --enable

# 3. Enable AWS Config
# Tracks resource configuration changes

# 4. Enable VPC Flow Logs
# Monitor network traffic to/from OpenSearch

# 5. Set up CloudTrail
# Audit all API calls
aws cloudtrail create-trail \
  --name gka-audit-trail \
  --s3-bucket-name my-audit-bucket
```

---

## 🔧 **Troubleshooting**

### **Issue: Terraform apply fails at OpenSearch**

**Error:** "Resource creation timeout"

**Solution:**
```bash
# OpenSearch takes 10-15 minutes to create
# Wait and check status
aws opensearch describe-domain --domain-name gka-vector-search

# If stuck in "Processing" for > 20 minutes:
# 1. Check service quotas
aws service-quotas list-service-quotas \
  --service-code es | grep -i instance

# 2. Try different instance type
# Edit iac/opensearch.tf
instance_type = "r6g.xlarge.search"  # or t3.small.search for dev
```

### **Issue: Lambda timeout errors**

**Error:** "Task timed out after 60.00 seconds"

**Solution:**
```bash
# 1. Increase timeout in iac/lambda.tf
timeout = 300  # 5 minutes

# 2. Check Lambda logs
aws logs tail /aws/lambda/gka-document-processor --follow

# 3. Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=gka-document-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

### **Issue: DynamoDB throttling**

**Error:** "ProvisionedThroughputExceededException"

**Solution:**
```bash
# On-demand mode should auto-scale, but check:
aws dynamodb describe-table --table-name gka-metadata

# If you switched to provisioned mode, increase capacity:
aws dynamodb update-table \
  --table-name gka-metadata \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# Or switch back to on-demand:
aws dynamodb update-table \
  --table-name gka-metadata \
  --billing-mode PAY_PER_REQUEST
```

### **Issue: S3 access denied**

**Error:** "Access Denied" when Lambda accesses S3

**Solution:**
```bash
# 1. Check IAM role policy
aws iam get-role-policy \
  --role-name gka-lambda-execution-role \
  --policy-name gka-lambda-execution-policy

# 2. Verify bucket policy
aws s3api get-bucket-policy --bucket gka-documents-123456

# 3. Check if bucket exists
aws s3 ls s3://gka-documents-123456

# 4. Test with AWS CLI
aws s3 cp test.txt s3://gka-documents-123456/test.txt
```

---

## 🔄 **Upgrading**

### **Update OpenSearch Version:**

```hcl
# Edit iac/opensearch.tf
engine_version = "OpenSearch_2.11"  # or newer

# Apply
terraform apply
```

**Note:** OpenSearch upgrades can take 30-60 minutes

### **Scale OpenSearch:**

```hcl
# Edit iac/opensearch.tf
instance_count = 4  # from 2

# Apply
terraform apply
```

### **Update Lambda Runtime:**

```hcl
# Edit iac/lambda.tf
runtime = "python3.11"  # from python3.10

# Rebuild Lambda package
cd lambda
pip install -r requirements.txt -t .
zip -r lambda_package.zip .

# Apply
terraform apply
```

---

## 🗑️ **Cleanup**

### **Destroy Infrastructure:**

```bash
cd iac

# Destroy all resources
terraform destroy

# Confirm when prompted
# This will delete:
# - All S3 objects
# - OpenSearch domain
# - DynamoDB tables (data will be lost!)
# - Lambda functions
# - API Gateway
# - CloudWatch logs
```

**Note:** Some resources may have deletion protection:
- OpenSearch domain snapshots
- DynamoDB table backups
- S3 versioned objects

### **Manual Cleanup:**

```bash
# 1. Empty S3 bucket
aws s3 rm s3://gka-documents-123456 --recursive

# 2. Delete S3 versions (if versioning enabled)
aws s3api delete-object-versions --bucket gka-documents-123456

# 3. Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /aws/lambda/gka-document-processor
aws logs delete-log-group --log-group-name /aws/lambda/gka-query-handler

# 4. Delete Secrets
aws secretsmanager delete-secret \
  --secret-id gka-opensearch-password \
  --force-delete-without-recovery
```

---

## 📚 **Next Steps**

1. ✅ **Phase 1 Complete** - Infrastructure deployed
2. ➡️ **Phase 2** - Implement document processing pipeline
3. ⏭️ **Phase 3** - Build RAG system
4. ⏭️ **Phase 4** - Add model selection & optimization
5. ⏭️ **Phase 5** - Implement safety & governance
6. ⏭️ **Phase 6** - Add monitoring & evaluation
7. ⏭️ **Phase 7** - Deploy web interface

---

## 🆘 **Support**

### **Common Commands:**

```bash
# Check infrastructure status
terraform show

# Get specific output
terraform output api_url

# Refresh state
terraform refresh

# Import existing resource
terraform import aws_s3_bucket.documents gka-documents-123456

# Validate configuration
terraform validate

# Format code
terraform fmt -recursive
```

### **Useful AWS CLI Commands:**

```bash
# List all Lambda functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `gka`)].FunctionName'

# List all DynamoDB tables
aws dynamodb list-tables --query 'TableNames[?starts_with(@, `gka`)]'

# List all S3 buckets
aws s3 ls | grep gka

# Check OpenSearch domain
aws opensearch list-domain-names
```

---

## ✅ **Verification Checklist**

After deployment, verify:

- [ ] API Gateway accessible (GET /documents returns 200 or 403)
- [ ] Lambda functions created (2 functions)
- [ ] S3 bucket created and accessible
- [ ] OpenSearch cluster healthy (green or yellow)
- [ ] DynamoDB tables created (3 tables)
- [ ] CloudWatch log groups exist
- [ ] CloudWatch dashboard created
- [ ] Secrets Manager secret created
- [ ] IAM roles created
- [ ] All terraform outputs available

**All checks passed? Ready for Phase 2!** ✅

