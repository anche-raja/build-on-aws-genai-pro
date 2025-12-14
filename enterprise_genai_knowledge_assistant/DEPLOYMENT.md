# Deployment Guide

Complete deployment guide for the Enterprise GenAI Knowledge Assistant.

## Prerequisites

- AWS Account with admin access
- AWS CLI configured (`aws configure`)
- Terraform >= 1.0
- Python 3.10+
- Node.js 18+

## Quick Deployment

```bash
# 1. Build Lambda functions
./build-lambda.sh

# 2. Deploy infrastructure
cd iac
terraform init
terraform apply

# 3. Get outputs
terraform output

# 4. Update web app with API Gateway URL
cd ../web
# Edit src/aws-exports.js with your values

# 5. Deploy web interface
npm install
npm run build
```

## Detailed Steps

### Step 1: Build Lambda Packages

```bash
./build-lambda.sh
```

This installs Python dependencies and creates deployment packages for all 5 Lambda functions:
- document_processor
- query_handler  
- quality_reporter
- analytics_exporter
- audit_exporter

### Step 2: Deploy Infrastructure with Terraform

```bash
cd iac
terraform init
terraform plan
terraform apply -auto-approve
```

This creates:
- 5 Lambda functions with proper IAM roles
- OpenSearch domain for vector search
- 6 DynamoDB tables (metadata, conversations, evaluations, etc.)
- S3 buckets (documents, audit logs, analytics)
- API Gateway with REST endpoints
- Bedrock guardrails for content safety
- CloudWatch dashboards and alarms
- SNS topics for alerts
- EventBridge rules for scheduled tasks

**Deployment Time:** ~20-30 minutes (OpenSearch takes longest)

### Step 3: Configure Web Application

After Terraform deployment, get the API Gateway URL:

```bash
terraform output api_gateway_url
# Output: https://xxxxx.execute-api.us-east-1.amazonaws.com/prod
```

Update `web/src/aws-exports.js`:

```javascript
const awsConfig = {
  aws_project_region: 'us-east-1',
  aws_cognito_region: 'us-east-1',
  aws_user_pools_id: 'us-east-1_xxxxxx',  // From Terraform output
  aws_user_pools_web_client_id: 'xxxxxxxxx',  // From Terraform output
  API: {
    endpoints: [
      {
        name: 'GenAIAPI',
        endpoint: 'https://xxxxx.execute-api.us-east-1.amazonaws.com/prod'
      }
    ]
  },
  Storage: {
    AWSS3: {
      bucket: 'gka-documents-xxxxxxxx',  // From Terraform output
      region: 'us-east-1'
    }
  }
};

export default awsConfig;
```

### Step 4: Deploy Web Interface

#### Option A: AWS Amplify (Recommended)

```bash
cd web
npm install
amplify init
amplify add hosting
amplify publish
```

#### Option B: S3 + CloudFront

```bash
cd web
npm install
npm run build

# Upload to S3
aws s3 sync build/ s3://your-website-bucket/

# Create CloudFront distribution (one-time)
# Point to S3 bucket
```

#### Option C: Local Development

```bash
cd web
npm install
npm start
# Opens at http://localhost:3000
```

### Step 5: Verify Deployment

#### Test Lambda Functions

```bash
# Test document processor
aws lambda invoke \
  --function-name gka-document-processor \
  --payload '{"body": "{\"test\": true}"}' \
  output.json && cat output.json

# Test query handler
aws lambda invoke \
  --function-name gka-query-handler \
  --payload '{"body": "{\"query\": \"test\"}"}' \
  output.json && cat output.json
```

#### Test API Gateway

```bash
# Get API URL
API_URL=$(cd iac && terraform output -raw api_gateway_url)

# Test query endpoint
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this system?"}'

# Test document endpoint
curl -X POST ${API_URL}/documents \
  -H "Content-Type: application/json" \
  -d '{"document_key": "test.txt", "document_type": "text"}'
```

#### Test Web Application

1. Open web app URL
2. Sign up / Log in
3. Upload a test document
4. Wait for processing (check CloudWatch logs)
5. Query the knowledge base

## Update Deployment

### Update Lambda Functions Only

```bash
# Rebuild packages
./build-lambda.sh

# Deploy all functions
for func in document_processor query_handler quality_reporter analytics_exporter audit_exporter; do
  echo "Updating $func..."
  cd lambda/$func/package
  zip -r ../deploy.zip . -q
  aws lambda update-function-code \
    --function-name gka-$func \
    --zip-file fileb://../deploy.zip
  cd ../../..
done
```

### Update Single Lambda Function

```bash
cd lambda/<function-name>/package
zip -r ../deploy.zip .
aws lambda update-function-code \
  --function-name gka-<function-name> \
  --zip-file fileb://../deploy.zip
```

### Update Infrastructure

```bash
cd iac
terraform plan
terraform apply
```

### Update Web Application

```bash
cd web
npm run build

# If using Amplify
amplify publish

# If using S3
aws s3 sync build/ s3://your-website-bucket/ --delete
```

## Troubleshooting

### Lambda Returns 502 Error

**Problem:** Missing Python dependencies

**Solution:**
```bash
./build-lambda.sh
cd lambda/<function-name>/package
zip -r ../deploy.zip .
aws lambda update-function-code \
  --function-name gka-<function-name> \
  --zip-file fileb://../deploy.zip
```

### OpenSearch Timeout

**Problem:** OpenSearch domain not accessible from Lambda

**Solution:** Check security groups and VPC configuration in Terraform

### Terraform Apply Fails

**Problem:** Insufficient permissions or resource limits

**Solutions:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check service quotas in AWS Console
- Review Terraform error message for specific resource

### Web App Can't Upload Documents

**Problem:** CORS or authentication issues

**Solutions:**
- Check API Gateway CORS configuration
- Verify Cognito user pool settings
- Check browser console for errors
- Ensure aws-exports.js is correctly configured

## Monitoring Deployment

### CloudWatch Dashboards

```bash
# View quality dashboard
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=gka-quality"

# View governance dashboard  
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=gka-governance"
```

### Lambda Logs

```bash
# Document processor
aws logs tail /aws/lambda/gka-document-processor --follow

# Query handler
aws logs tail /aws/lambda/gka-query-handler --follow

# Quality reporter
aws logs tail /aws/lambda/gka-quality-reporter --follow
```

### Check S3 Buckets

```bash
# List documents
aws s3 ls s3://gka-documents-<account-id>/

# List analytics reports
aws s3 ls s3://gka-analytics-exports-<account-id>/quality-reports/

# List audit logs
aws s3 ls s3://gka-audit-logs-<account-id>/audit-exports/
```

### Check DynamoDB Tables

```bash
# List metadata
aws dynamodb scan --table-name gka-metadata --max-items 5

# List conversations
aws dynamodb scan --table-name gka-conversations --max-items 5

# List feedback
aws dynamodb scan --table-name gka-user-feedback --max-items 5
```

## Production Deployment Checklist

- [ ] All Lambda functions deployed with dependencies
- [ ] OpenSearch domain is healthy and accessible
- [ ] DynamoDB tables created
- [ ] S3 buckets configured with proper policies
- [ ] API Gateway endpoints responding
- [ ] Bedrock model access enabled in account
- [ ] Cognito user pool configured
- [ ] CloudWatch dashboards displaying metrics
- [ ] SNS topics subscribed for alerts
- [ ] Web application deployed and accessible
- [ ] Test document upload works
- [ ] Test query returns results
- [ ] Scheduled tasks configured (EventBridge rules)
- [ ] Backup policies enabled (DynamoDB PITR, S3 versioning)
- [ ] Cost alerts configured
- [ ] Security scan completed

## Cost Estimates

**Monthly Costs (Moderate Usage):**
- Lambda: $20-50 (5 functions, ~10K invocations/month)
- OpenSearch: $100-200 (t3.small.search instance)
- Bedrock: $50-200 (varies by usage and model)
- DynamoDB: $5-10 (Pay-per-request mode)
- S3: $5-10 (storage and requests)
- API Gateway: $3-5 (~10K requests)
- CloudWatch: $10-15 (logs and metrics)
- **Total: ~$200-500/month**

## Cleanup / Teardown

To destroy all resources:

```bash
cd iac
terraform destroy -auto-approve
```

**Warning:** This deletes all data including:
- Documents in S3
- OpenSearch indices
- DynamoDB tables
- Audit logs
- Analytics reports

Make sure to backup any important data before destroying!

## Support

For deployment issues:
1. Check CloudWatch Logs for error details
2. Review Terraform output for resource IDs
3. Verify AWS service quotas
4. Check IAM permissions

---

Last Updated: December 2025
