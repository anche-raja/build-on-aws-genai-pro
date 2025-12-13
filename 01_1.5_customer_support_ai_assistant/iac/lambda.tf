# Lambda Functions for Customer Support AI Assistant

# Package Lambda functions
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/lambda_package.zip"
  excludes = [
    "iac",
    "tests",
    "*.md",
    ".git",
    ".gitignore",
    "__pycache__",
    "*.pyc"
  ]
}

# Capture Query Lambda
resource "aws_lambda_function" "capture_query" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-capture-query-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_capture_query.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      CONVERSATION_TABLE = aws_dynamodb_table.conversations.name
      AWS_REGION         = var.aws_region
      ENVIRONMENT        = var.environment
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-capture-query-${var.environment}"
      Type = "CaptureQuery"
    }
  )
}

# Detect Intent Lambda
resource "aws_lambda_function" "detect_intent" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-detect-intent-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_detect_intent.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      CONVERSATION_TABLE = aws_dynamodb_table.conversations.name
      AWS_REGION         = var.aws_region
      ENVIRONMENT        = var.environment
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-detect-intent-${var.environment}"
      Type = "IntentDetection"
    }
  )
}

# Generate Response Lambda
resource "aws_lambda_function" "generate_response" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-generate-response-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_generate_response.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  timeout          = 120  # Longer timeout for Bedrock invocation
  memory_size      = 1024  # More memory for Bedrock

  environment {
    variables = {
      CONVERSATION_TABLE = aws_dynamodb_table.conversations.name
      PROMPT_TABLE       = aws_dynamodb_table.prompts.name
      PROMPT_BUCKET      = aws_s3_bucket.prompt_templates.bucket
      AWS_REGION         = var.aws_region
      MODEL_ID           = var.bedrock_model_id
      ENVIRONMENT        = var.environment
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-generate-response-${var.environment}"
      Type = "ResponseGeneration"
    }
  )
}

# Validate Quality Lambda
resource "aws_lambda_function" "validate_quality" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-validate-quality-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_validate_quality.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      QUALITY_THRESHOLD = var.quality_threshold
      AWS_REGION        = var.aws_region
      ENVIRONMENT       = var.environment
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-validate-quality-${var.environment}"
      Type = "QualityValidation"
    }
  )
}

# Collect Feedback Lambda
resource "aws_lambda_function" "collect_feedback" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-collect-feedback-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_collect_feedback.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      FEEDBACK_TABLE = aws_dynamodb_table.feedback.name
      AWS_REGION     = var.aws_region
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-collect-feedback-${var.environment}"
      Type = "FeedbackCollection"
    }
  )
}

# Analyze Feedback Lambda (for scheduled analysis)
resource "aws_lambda_function" "analyze_feedback" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-analyze-feedback-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "lambda_collect_feedback.analyze_feedback_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  timeout          = 300  # 5 minutes for analysis
  memory_size      = 1024

  environment {
    variables = {
      FEEDBACK_TABLE = aws_dynamodb_table.feedback.name
      AWS_REGION     = var.aws_region
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-analyze-feedback-${var.environment}"
      Type = "FeedbackAnalysis"
    }
  )
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "capture_query" {
  name              = "/aws/lambda/${aws_lambda_function.capture_query.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "detect_intent" {
  name              = "/aws/lambda/${aws_lambda_function.detect_intent.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "generate_response" {
  name              = "/aws/lambda/${aws_lambda_function.generate_response.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "validate_quality" {
  name              = "/aws/lambda/${aws_lambda_function.validate_quality.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "collect_feedback" {
  name              = "/aws/lambda/${aws_lambda_function.collect_feedback.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "analyze_feedback" {
  name              = "/aws/lambda/${aws_lambda_function.analyze_feedback.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = var.tags
}

# Outputs
output "capture_query_function_arn" {
  description = "Capture Query Lambda function ARN"
  value       = aws_lambda_function.capture_query.arn
}

output "detect_intent_function_arn" {
  description = "Detect Intent Lambda function ARN"
  value       = aws_lambda_function.detect_intent.arn
}

output "generate_response_function_arn" {
  description = "Generate Response Lambda function ARN"
  value       = aws_lambda_function.generate_response.arn
}

output "validate_quality_function_arn" {
  description = "Validate Quality Lambda function ARN"
  value       = aws_lambda_function.validate_quality.arn
}

output "collect_feedback_function_arn" {
  description = "Collect Feedback Lambda function ARN"
  value       = aws_lambda_function.collect_feedback.arn
}

output "analyze_feedback_function_arn" {
  description = "Analyze Feedback Lambda function ARN"
  value       = aws_lambda_function.analyze_feedback.arn
}


