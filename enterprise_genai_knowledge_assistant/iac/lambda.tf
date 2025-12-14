# Create build directory for Lambda artifacts
resource "null_resource" "create_build_dir" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/../build"
  }
}

# Auto-build Lambda packages with dependencies
resource "null_resource" "build_query_handler" {
  depends_on = [null_resource.create_build_dir]
  triggers = {
    # Rebuild when source code changes
    code_hash = filemd5("${path.module}/../lambda/query_handler/app.py")
    requirements_hash = filemd5("${path.module}/../lambda/query_handler/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      cd ${path.module}/../lambda/query_handler
      rm -rf package
      mkdir -p package
      python3 -m pip install -r requirements.txt -t package/ --quiet
      cp *.py package/
      echo "✅ Query handler built"
    EOT
  }
}

resource "null_resource" "build_document_processor" {
  depends_on = [null_resource.create_build_dir]
  
  triggers = {
    code_hash = filemd5("${path.module}/../lambda/document_processor/app.py")
    requirements_hash = filemd5("${path.module}/../lambda/document_processor/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      cd ${path.module}/../lambda/document_processor
      rm -rf package
      mkdir -p package
      python3 -m pip install -r requirements.txt -t package/ --quiet
      cp *.py package/
      echo "✅ Document processor built"
    EOT
  }
}

# Data source for Lambda package archives
data "archive_file" "document_processor" {
  depends_on = [null_resource.build_document_processor]
  type        = "zip"
  source_dir  = "${path.module}/../lambda/document_processor/package"
  output_path = "${path.module}/../build/lambda_document_processor.zip"
}

data "archive_file" "query_handler" {
  depends_on = [null_resource.build_query_handler]
  type        = "zip"
  source_dir  = "${path.module}/../lambda/query_handler/package"
  output_path = "${path.module}/../build/lambda_query_handler.zip"
}

resource "null_resource" "build_quality_reporter" {
  depends_on = [null_resource.create_build_dir]
  
  triggers = {
    code_hash = filemd5("${path.module}/../lambda/quality_reporter/app.py")
    requirements_hash = filemd5("${path.module}/../lambda/quality_reporter/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      cd ${path.module}/../lambda/quality_reporter
      rm -rf package
      mkdir -p package
      python3 -m pip install -r requirements.txt -t package/ --quiet
      cp *.py package/
      echo "✅ Quality reporter built"
    EOT
  }
}

resource "null_resource" "build_analytics_exporter" {
  depends_on = [null_resource.create_build_dir]
  
  triggers = {
    code_hash = filemd5("${path.module}/../lambda/analytics_exporter/app.py")
    requirements_hash = filemd5("${path.module}/../lambda/analytics_exporter/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      cd ${path.module}/../lambda/analytics_exporter
      rm -rf package
      mkdir -p package
      python3 -m pip install -r requirements.txt -t package/ --quiet
      cp *.py package/
      echo "✅ Analytics exporter built"
    EOT
  }
}

resource "null_resource" "build_audit_exporter" {
  depends_on = [null_resource.create_build_dir]
  
  triggers = {
    code_hash = filemd5("${path.module}/../lambda/audit_exporter/app.py")
    requirements_hash = filemd5("${path.module}/../lambda/audit_exporter/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      cd ${path.module}/../lambda/audit_exporter
      rm -rf package
      mkdir -p package
      python3 -m pip install -r requirements.txt -t package/ --quiet
      cp *.py package/
      echo "✅ Audit exporter built"
    EOT
  }
}

data "archive_file" "quality_reporter" {
  depends_on = [null_resource.build_quality_reporter]
  type        = "zip"
  source_dir  = "${path.module}/../lambda/quality_reporter/package"
  output_path = "${path.module}/../build/lambda_quality_reporter.zip"
}

data "archive_file" "analytics_exporter" {
  depends_on = [null_resource.build_analytics_exporter]
  type        = "zip"
  source_dir  = "${path.module}/../lambda/analytics_exporter/package"
  output_path = "${path.module}/../build/lambda_analytics_exporter.zip"
}

data "archive_file" "audit_exporter" {
  depends_on = [null_resource.build_audit_exporter]
  type        = "zip"
  source_dir  = "${path.module}/../lambda/audit_exporter/package"
  output_path = "${path.module}/../build/lambda_audit_exporter.zip"
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

