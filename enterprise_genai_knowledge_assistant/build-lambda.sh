#!/bin/bash

# Build Lambda deployment packages with dependencies
# Updated for separate Lambda directories with shared modules

set -e

echo "Building Lambda deployment packages..."

# Function to build Lambda package
build_lambda() {
    local lambda_dir=$1
    local lambda_name=$2
    local needs_shared=$3
    
    echo "Building $lambda_name..."
    
    cd "$lambda_dir"
    
    # Clean up any existing packages
    rm -rf package
    mkdir -p package
    
    # Install dependencies to package directory
    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies for $lambda_name..."
        python3 -m pip install -r requirements.txt -t package/ --trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade
        
        # Copy application code
        cp *.py package/ 2>/dev/null || true
        
        # Copy shared modules if needed
        if [ "$needs_shared" = "true" ] && [ -d "../shared" ]; then
            echo "Copying shared modules for $lambda_name..."
            cp ../shared/*.py package/
        fi
        
        echo "✓ $lambda_name built successfully"
    else
        echo "⚠ No requirements.txt found for $lambda_name"
    fi
    
    cd - > /dev/null
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_DIR="$SCRIPT_DIR/lambda"

# Build all Lambda functions
build_lambda "$LAMBDA_DIR/document_processor" "document_processor" "false"
build_lambda "$LAMBDA_DIR/query_handler" "query_handler" "true"
build_lambda "$LAMBDA_DIR/quality_reporter" "quality_reporter" "false"
build_lambda "$LAMBDA_DIR/analytics_exporter" "analytics_exporter" "false"
build_lambda "$LAMBDA_DIR/audit_exporter" "audit_exporter" "false"

echo ""
echo "✓ All Lambda packages built successfully!"
echo ""
echo "Lambda Functions:"
echo "  1. document_processor   (standalone)"
echo "  2. query_handler        (uses shared modules)"
echo "  3. quality_reporter     (standalone)"
echo "  4. analytics_exporter   (standalone)"
echo "  5. audit_exporter       (standalone)"
echo ""
echo "Next step: Deploy with Terraform or AWS CLI"
echo "  cd iac && terraform apply"
