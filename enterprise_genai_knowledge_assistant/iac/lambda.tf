# Data source for Lambda package archives
data "archive_file" "document_processor" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/document_processor"
  output_path = "${path.module}/lambda_document_processor.zip"
}

data "archive_file" "query_handler" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/query_handler"
  output_path = "${path.module}/lambda_query_handler.zip"
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "document_processor" {
  name              = "/aws/lambda/${var.project_name}-document-processor"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "query_handler" {
  name              = "/aws/lambda/${var.project_name}-query-handler"
  retention_in_days = 14
}

# Document Processor Lambda Function
resource "aws_lambda_function" "document_processor" {
  filename         = data.archive_file.document_processor.output_path
  function_name    = "${var.project_name}-document-processor"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "app.handler"
  source_code_hash = data.archive_file.document_processor.output_base64sha256
  runtime          = "python3.10"
  timeout          = var.document_processor_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      DOCUMENT_BUCKET    = aws_s3_bucket.document_bucket.id
      METADATA_TABLE     = aws_dynamodb_table.metadata_table.name
      OPENSEARCH_DOMAIN  = aws_opensearch_domain.vector_search.endpoint
      OPENSEARCH_SECRET  = aws_secretsmanager_secret.opensearch_password.name
    }
  }

  depends_on = [
    aws_iam_role_policy.bedrock_policy,
    aws_iam_role_policy.services_policy
  ]

  tags = {
    Name = "${var.project_name}-document-processor"
  }
}

# Query Handler Lambda Function
resource "aws_lambda_function" "query_handler" {
  filename         = data.archive_file.query_handler.output_path
  function_name    = "${var.project_name}-query-handler"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "app.handler"
  source_code_hash = data.archive_file.query_handler.output_base64sha256
  runtime          = "python3.10"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      METADATA_TABLE      = aws_dynamodb_table.metadata_table.name
      CONVERSATION_TABLE  = aws_dynamodb_table.conversation_table.name
      OPENSEARCH_DOMAIN   = aws_opensearch_domain.vector_search.endpoint
      OPENSEARCH_SECRET   = aws_secretsmanager_secret.opensearch_password.name
      EVALUATION_TABLE    = aws_dynamodb_table.evaluation_table.name
      AUDIT_TRAIL_TABLE   = aws_dynamodb_table.audit_trail.name
      GUARDRAIL_ID        = aws_bedrock_guardrail.content_safety.guardrail_id
      GUARDRAIL_VERSION   = "DRAFT"
      COMPLIANCE_SNS      = aws_sns_topic.compliance_alerts.arn
      AUDIT_LOGS_BUCKET   = aws_s3_bucket.audit_logs.id
      USER_FEEDBACK_TABLE = aws_dynamodb_table.user_feedback.name
      QUALITY_METRICS_TABLE = aws_dynamodb_table.quality_metrics.name
      QUALITY_LOG_GROUP   = aws_cloudwatch_log_group.quality_metrics.name
    }
  }

  depends_on = [
    aws_iam_role_policy.bedrock_policy,
    aws_iam_role_policy.services_policy
  ]

  tags = {
    Name = "${var.project_name}-query-handler"
  }
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "document_processor_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_processor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.genai_knowledge_assistant.execution_arn}/*/*"
}

resource "aws_lambda_permission" "query_handler_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.genai_knowledge_assistant.execution_arn}/*/*"
}

