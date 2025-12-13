# Deployment Guide

This guide provides step-by-step instructions for deploying the AWS Customer Support AI Assistant.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Setup](#pre-deployment-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Testing](#testing)
6. [Monitoring Setup](#monitoring-setup)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### AWS Account Requirements

- **AWS Account**: Active AWS account with appropriate permissions
- **IAM Permissions**: Administrator access or equivalent permissions for:
  - Lambda
  - Step Functions
  - API Gateway
  - DynamoDB
  - S3
  - CloudWatch
  - CloudTrail
  - IAM
  - Bedrock

### Bedrock Access

1. **Enable Bedrock** in your AWS account:
   ```bash
   # Check if Bedrock is available in your region
   aws bedrock list-foundation-models --region us-east-1
   ```

2. **Request Model Access**:
   - Go to AWS Console → Bedrock → Model Access
   - Request access to Claude 3 Sonnet
   - Wait for approval (usually instant)

### Local Development Tools

- **Terraform**: >= 1.0
  ```bash
  terraform version
  ```

- **AWS CLI**: >= 2.0
  ```bash
  aws --version
  ```

- **Python**: >= 3.11
  ```bash
  python --version
  ```

- **Git**: For version control
  ```bash
  git --version
  ```

## Pre-Deployment Setup

### 1. Clone the Repository

```bash
cd /path/to/workspace
cd 01_1.5_customer_support_ai_assistant
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify credentials
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

### 4. Choose Deployment Region

```bash
# Bedrock is available in limited regions
# Recommended regions:
# - us-east-1 (N. Virginia)
# - us-west-2 (Oregon)
# - eu-central-1 (Frankfurt)
# - ap-northeast-1 (Tokyo)

export AWS_REGION=us-east-1
```

## Infrastructure Deployment

### Step 1: Initialize Terraform

```bash
cd iac

# Initialize Terraform
terraform init
```

Expected output:
```
Initializing the backend...
Initializing provider plugins...
...
Terraform has been successfully initialized!
```

### Step 2: Configure Variables

```bash
# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your settings
nano terraform.tfvars
```

**Key Variables to Configure**:

```hcl
# terraform.tfvars

project_name = "customer-support-ai"
environment  = "dev"  # or "prod", "staging"
aws_region   = "us-east-1"

# Bedrock Configuration
bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# Quality Settings
quality_threshold = 70

# Monitoring
enable_cloudtrail = true
enable_xray       = true

# Tags
tags = {
  Project     = "CustomerSupportAI"
  ManagedBy   = "Terraform"
  Environment = "dev"
  Owner       = "your-email@example.com"
}
```

### Step 3: Review Deployment Plan

```bash
# Generate and review execution plan
terraform plan -out=tfplan

# Review the plan carefully
# Should show resources to be created:
# - 3 DynamoDB tables
# - 3 S3 buckets
# - 6 Lambda functions
# - 1 Step Functions state machine
# - 1 API Gateway
# - IAM roles and policies
# - CloudWatch resources
# - EventBridge rules
```

### Step 4: Deploy Infrastructure

```bash
# Apply the plan
terraform apply tfplan

# Confirm by typing: yes
```

**Deployment Time**: Approximately 5-10 minutes

Expected output:
```
Apply complete! Resources: 50+ added, 0 changed, 0 destroyed.

Outputs:

api_gateway_url = "https://abc123.execute-api.us-east-1.amazonaws.com/dev"
conversations_table = "customer-support-ai-conversations-dev"
dashboard_url = "https://console.aws.amazon.com/cloudwatch/..."
...
```

### Step 5: Save Outputs

```bash
# Save all outputs to a file
terraform output -json > deployment_outputs.json

# View specific outputs
terraform output api_gateway_url
terraform output workflow_arn
```

## Post-Deployment Configuration

### 1. Verify Lambda Functions

```bash
# List deployed functions
aws lambda list-functions \
  --query "Functions[?contains(FunctionName, 'customer-support-ai')].FunctionName"

# Test a function
aws lambda invoke \
  --function-name customer-support-ai-capture-query-dev \
  --payload '{"query": "test", "user_id": "test-user"}' \
  response.json

cat response.json
```

### 2. Verify Step Functions

```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(terraform output -raw workflow_arn)

# Describe state machine
aws stepfunctions describe-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN
```

### 3. Verify API Gateway

```bash
# Get API URL
API_URL=$(terraform output -raw api_gateway_url)

# Test health (should return 403 without proper request)
curl $API_URL/query
```

### 4. Initialize Prompt Templates (Optional)

```bash
# Create sample prompt template
python << EOF
import boto3
import json

s3 = boto3.client('s3')
bucket_name = '$(terraform output -raw prompt_templates_bucket)'

template = {
    'name': 'General Support',
    'template': 'You are a helpful AWS support assistant...',
    'parameters': ['query', 'history']
}

s3.put_object(
    Bucket=bucket_name,
    Key='prompts/general_support/1.0.0.json',
    Body=json.dumps(template),
    ContentType='application/json'
)

print("Template uploaded successfully")
EOF
```

## Testing

### 1. Unit Tests

```bash
# Run unit tests
cd ..
./tests/run_tests.sh
```

### 2. Integration Test

```bash
# Get API endpoint
API_URL=$(cd iac && terraform output -raw api_gateway_url)

# Test EC2 troubleshooting query
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My EC2 instance is not responding to SSH connections. How can I troubleshoot this?",
    "user_id": "test-user-123"
  }' | jq '.'
```

Expected response:
```json
{
  "statusCode": 200,
  "body": {
    "session_id": "...",
    "response": "I understand you're experiencing...",
    "intent": "ec2_troubleshooting",
    "confidence": 0.95,
    "quality_score": 85.5
  }
}
```

### 3. Test Different Scenarios

```bash
# Test S3 issue
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I am getting access denied when uploading to my S3 bucket",
    "user_id": "test-user-123"
  }' | jq '.body.intent'

# Test vague query (should request clarification)
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need help with AWS",
    "user_id": "test-user-123"
  }' | jq '.body.response'

# Test guardrails (should block)
curl -X POST ${API_URL}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My access key is AKIAIOSFODNN7EXAMPLE",
    "user_id": "test-user-123"
  }' | jq '.body.response'
```

### 4. Test Feedback Endpoint

```bash
curl -X POST ${API_URL}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "interaction_id": "test-interaction-456",
    "feedback_type": "thumbs_up",
    "rating": 5,
    "comments": "Very helpful!"
  }' | jq '.'
```

## Monitoring Setup

### 1. Access CloudWatch Dashboard

```bash
# Get dashboard URL
DASHBOARD_URL=$(cd iac && terraform output -raw dashboard_url)

echo "Dashboard URL: $DASHBOARD_URL"
# Open in browser
```

### 2. Configure CloudWatch Alarms

```bash
# Verify alarms are created
aws cloudwatch describe-alarms \
  --alarm-name-prefix "customer-support-ai"
```

### 3. Set Up SNS Notifications (Optional)

```bash
# Create SNS topic for alerts
aws sns create-topic --name customer-support-ai-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:customer-support-ai-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Update alarms to use SNS topic
# (Add AlarmActions to monitoring.tf and redeploy)
```

### 4. Enable X-Ray Insights (if enabled)

```bash
# View X-Ray service map
aws xray get-service-graph \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s)
```

## Post-Deployment Validation

### Validation Checklist

- [ ] All Lambda functions deployed and invocable
- [ ] Step Functions state machine created
- [ ] API Gateway endpoints accessible
- [ ] DynamoDB tables created with correct configuration
- [ ] S3 buckets created with versioning enabled
- [ ] IAM roles and policies configured correctly
- [ ] CloudWatch logs being generated
- [ ] CloudWatch dashboard accessible
- [ ] CloudTrail logging enabled (if configured)
- [ ] X-Ray tracing working (if enabled)
- [ ] Test queries returning valid responses
- [ ] Guardrails blocking sensitive input
- [ ] Quality validation working
- [ ] Feedback collection functioning

### Validation Script

```bash
#!/bin/bash

echo "Validating Customer Support AI Assistant Deployment"
echo "=================================================="

cd iac

# Check Lambda functions
echo "Checking Lambda functions..."
for func in capture-query detect-intent generate-response validate-quality collect-feedback analyze-feedback; do
  if aws lambda get-function --function-name "customer-support-ai-${func}-dev" &>/dev/null; then
    echo "✓ $func Lambda exists"
  else
    echo "✗ $func Lambda missing"
  fi
done

# Check DynamoDB tables
echo -e "\nChecking DynamoDB tables..."
for table in conversations prompts feedback; do
  if aws dynamodb describe-table --table-name "customer-support-ai-${table}-dev" &>/dev/null; then
    echo "✓ $table table exists"
  else
    echo "✗ $table table missing"
  fi
done

# Check API Gateway
echo -e "\nChecking API Gateway..."
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null)
if [ -n "$API_URL" ]; then
  echo "✓ API Gateway deployed: $API_URL"
else
  echo "✗ API Gateway not found"
fi

# Test API
echo -e "\nTesting API..."
if [ -n "$API_URL" ]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST ${API_URL}/query \
    -H "Content-Type: application/json" \
    -d '{"query": "test", "user_id": "test"}')
  
  if [ "$HTTP_CODE" == "200" ]; then
    echo "✓ API responding with 200 OK"
  else
    echo "✗ API returned HTTP $HTTP_CODE"
  fi
fi

echo -e "\n=================================================="
echo "Validation complete!"
```

## Troubleshooting

### Common Issues

#### Issue 1: Terraform Apply Fails

**Error**: "Error creating Lambda function: InvalidParameterValueException"

**Solution**:
```bash
# Verify Python version in Lambda
cd iac
grep "runtime" lambda.tf

# Ensure runtime is supported
# Update if needed and reapply
```

#### Issue 2: Bedrock Access Denied

**Error**: "AccessDeniedException: Could not access model"

**Solution**:
```bash
# Request model access in Bedrock console
aws bedrock list-foundation-models --region us-east-1

# Verify your account has access to Claude 3
# Wait a few minutes after requesting access
```

#### Issue 3: API Gateway 403 Forbidden

**Error**: API returns 403 on query endpoint

**Solution**:
```bash
# Check API Gateway integration
aws apigateway get-integration \
  --rest-api-id YOUR_API_ID \
  --resource-id YOUR_RESOURCE_ID \
  --http-method POST

# Verify Step Functions execution role has correct permissions
```

#### Issue 4: Lambda Timeout

**Error**: Lambda function times out

**Solution**:
```bash
# Increase timeout in iac/lambda.tf
# For generate_response, use 120 seconds minimum

# Update Lambda configuration
aws lambda update-function-configuration \
  --function-name customer-support-ai-generate-response-dev \
  --timeout 120
```

### Viewing Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/customer-support-ai-capture-query-dev --follow

# View Step Functions logs
aws logs tail /aws/stepfunctions/customer-support-ai-workflow-dev --follow

# View API Gateway logs
aws logs tail /aws/apigateway/customer-support-ai-dev --follow
```

### Debug Mode

```bash
# Enable debug logging for Lambda
aws lambda update-function-configuration \
  --function-name customer-support-ai-generate-response-dev \
  --environment "Variables={LOG_LEVEL=DEBUG}"
```

## Cleanup

To remove all deployed resources:

```bash
cd iac

# Destroy all resources
terraform destroy

# Confirm by typing: yes
```

**Warning**: This will delete all data including conversation history and feedback.

## Next Steps

After successful deployment:

1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system details
2. Read [PROMPT_MANAGEMENT.md](PROMPT_MANAGEMENT.md) for prompt optimization
3. Set up continuous monitoring
4. Configure backups and disaster recovery
5. Implement authentication/authorization for production
6. Conduct security review
7. Perform load testing

## Support

For issues during deployment:
- Check CloudWatch logs for error details
- Review Terraform output for resource creation errors
- Consult [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Open an issue in the repository

---

**Deployment Time Estimate**: 30-45 minutes for first-time setup



