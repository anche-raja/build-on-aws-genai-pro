#!/bin/bash

# Setup script for RAG Vector Search System Infrastructure

set -e

echo "================================================"
echo "RAG Vector Search System - Infrastructure Setup"
echo "================================================"
echo ""

# Check for required tools
echo "Checking for required tools..."

if ! command -v terraform &> /dev/null; then
    echo "Error: Terraform is not installed. Please install Terraform first."
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install AWS CLI first."
    exit 1
fi

echo "✓ All required tools are installed"
echo ""

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✓ AWS credentials are configured"
echo ""

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo ""

# Prompt for bucket name
read -p "Enter a unique name for the S3 document bucket: " BUCKET_NAME

if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Bucket name cannot be empty"
    exit 1
fi

# Create terraform.tfvars if it doesn't exist
if [ ! -f "iac/terraform.tfvars" ]; then
    echo "Creating terraform.tfvars..."
    cp iac/terraform.tfvars.example iac/terraform.tfvars
    
    # Update bucket name
    sed -i.bak "s/document_bucket_name = .*/document_bucket_name = \"$BUCKET_NAME\"/" iac/terraform.tfvars
    sed -i.bak "s/aws_region = .*/aws_region = \"$AWS_REGION\"/" iac/terraform.tfvars
    rm iac/terraform.tfvars.bak
    
    echo "✓ Created terraform.tfvars"
else
    echo "terraform.tfvars already exists, skipping..."
fi

echo ""

# Package Lambda functions
echo "Packaging Lambda functions..."

cd "$(dirname "$0")"

# Create deployment packages directory
mkdir -p deployment_packages

# Package document processor
echo "  Packaging document processor..."
cd app
zip -r ../deployment_packages/lambda_document_processor.zip . > /dev/null 2>&1
cd ..
zip -g deployment_packages/lambda_document_processor.zip lambda_document_processor.py > /dev/null 2>&1

# Package sync scheduler
echo "  Packaging sync scheduler..."
cd app
zip -r ../deployment_packages/lambda_sync_scheduler.zip . > /dev/null 2>&1
cd ..
zip -g deployment_packages/lambda_sync_scheduler.zip lambda_sync_scheduler.py > /dev/null 2>&1

# Package RAG API
echo "  Packaging RAG API..."
cd app
zip -r ../deployment_packages/lambda_rag_api.zip . > /dev/null 2>&1
cd ..
zip -g deployment_packages/lambda_rag_api.zip lambda_rag_api.py > /dev/null 2>&1

# Move packages for Terraform
mv deployment_packages/*.zip . > /dev/null 2>&1

echo "✓ Lambda functions packaged"
echo ""

# Initialize and apply Terraform
echo "Initializing Terraform..."
cd iac
terraform init

echo ""
echo "Planning Terraform deployment..."
terraform plan -out=tfplan

echo ""
read -p "Do you want to apply this Terraform plan? (yes/no): " APPLY_PLAN

if [ "$APPLY_PLAN" = "yes" ]; then
    echo ""
    echo "Applying Terraform configuration..."
    terraform apply tfplan
    
    echo ""
    echo "================================================"
    echo "Infrastructure deployment complete!"
    echo "================================================"
    echo ""
    
    # Display outputs
    echo "Important endpoints and resources:"
    terraform output
    
    echo ""
    echo "Next steps:"
    echo "1. Enable Amazon Bedrock model access in the AWS Console"
    echo "2. Upload documents to the S3 bucket"
    echo "3. Test the RAG API endpoint"
    echo ""
else
    echo "Terraform apply cancelled."
fi

cd ..

