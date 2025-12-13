# S3 Buckets for Customer Support AI Assistant

# Prompt Templates Storage Bucket
resource "aws_s3_bucket" "prompt_templates" {
  bucket = "${var.project_name}-prompt-templates-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-prompt-templates-${var.environment}"
      Type = "PromptStorage"
    }
  )
}

resource "aws_s3_bucket_versioning" "prompt_templates" {
  bucket = aws_s3_bucket.prompt_templates.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "prompt_templates" {
  bucket = aws_s3_bucket.prompt_templates.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "prompt_templates" {
  bucket = aws_s3_bucket.prompt_templates.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "prompt_templates" {
  bucket = aws_s3_bucket.prompt_templates.id

  rule {
    id     = "archive-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

# Lambda Deployment Bucket
resource "aws_s3_bucket" "lambda_deployments" {
  bucket = "${var.project_name}-lambda-deployments-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-lambda-deployments-${var.environment}"
      Type = "LambdaDeployment"
    }
  )
}

resource "aws_s3_bucket_versioning" "lambda_deployments" {
  bucket = aws_s3_bucket.lambda_deployments.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "lambda_deployments" {
  bucket = aws_s3_bucket.lambda_deployments.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "lambda_deployments" {
  bucket = aws_s3_bucket.lambda_deployments.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Outputs
output "prompt_templates_bucket_name" {
  description = "Prompt templates S3 bucket name"
  value       = aws_s3_bucket.prompt_templates.bucket
}

output "prompt_templates_bucket_arn" {
  description = "Prompt templates S3 bucket ARN"
  value       = aws_s3_bucket.prompt_templates.arn
}

output "lambda_deployments_bucket_name" {
  description = "Lambda deployments S3 bucket name"
  value       = aws_s3_bucket.lambda_deployments.bucket
}


