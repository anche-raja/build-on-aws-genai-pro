# Lambda Function: Document Processor
resource "aws_lambda_function" "document_processor" {
  filename         = "${path.module}/../lambda_document_processor.zip"
  function_name    = "${var.project_name}-document-processor"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "lambda_document_processor.lambda_handler"
  source_code_hash = fileexists("${path.module}/../lambda_document_processor.zip") ? filebase64sha256("${path.module}/../lambda_document_processor.zip") : null
  runtime         = "python3.11"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  
  environment {
    variables = {
      METADATA_TABLE_NAME = aws_dynamodb_table.metadata.name
      OPENSEARCH_ENDPOINT = aws_opensearch_domain.vector_search.endpoint
      INDEX_NAME          = "documents"
      CHUNKING_STRATEGY   = "semantic"
      AWS_REGION          = var.aws_region
    }
  }
  
  tags = {
    Name = "${var.project_name}-document-processor"
  }
}

# Lambda Function: Sync Scheduler
resource "aws_lambda_function" "sync_scheduler" {
  filename         = "${path.module}/../lambda_sync_scheduler.zip"
  function_name    = "${var.project_name}-sync-scheduler"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "lambda_sync_scheduler.lambda_handler"
  source_code_hash = fileexists("${path.module}/../lambda_sync_scheduler.zip") ? filebase64sha256("${path.module}/../lambda_sync_scheduler.zip") : null
  runtime         = "python3.11"
  timeout         = var.lambda_timeout
  memory_size     = 512
  
  environment {
    variables = {
      METADATA_TABLE_NAME = aws_dynamodb_table.metadata.name
      BUCKET_NAME         = aws_s3_bucket.documents.id
      MAX_AGE_DAYS        = var.max_age_days
      STATE_MACHINE_ARN   = aws_sfn_state_machine.sync_workflow.arn
      AWS_REGION          = var.aws_region
    }
  }
  
  tags = {
    Name = "${var.project_name}-sync-scheduler"
  }
}

# Lambda Function: RAG API
resource "aws_lambda_function" "rag_api" {
  filename         = "${path.module}/../lambda_rag_api.zip"
  function_name    = "${var.project_name}-rag-api"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "lambda_rag_api.lambda_handler"
  source_code_hash = fileexists("${path.module}/../lambda_rag_api.zip") ? filebase64sha256("${path.module}/../lambda_rag_api.zip") : null
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = var.lambda_memory_size
  
  environment {
    variables = {
      OPENSEARCH_ENDPOINT = aws_opensearch_domain.vector_search.endpoint
      INDEX_NAME          = "documents"
      MODEL_ID            = var.foundation_model_id
      AWS_REGION          = var.aws_region
    }
  }
  
  tags = {
    Name = "${var.project_name}-rag-api"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "document_processor" {
  name              = "/aws/lambda/${aws_lambda_function.document_processor.function_name}"
  retention_in_days = 14
  
  tags = {
    Name = "${var.project_name}-document-processor-logs"
  }
}

resource "aws_cloudwatch_log_group" "sync_scheduler" {
  name              = "/aws/lambda/${aws_lambda_function.sync_scheduler.function_name}"
  retention_in_days = 14
  
  tags = {
    Name = "${var.project_name}-sync-scheduler-logs"
  }
}

resource "aws_cloudwatch_log_group" "rag_api" {
  name              = "/aws/lambda/${aws_lambda_function.rag_api.function_name}"
  retention_in_days = 14
  
  tags = {
    Name = "${var.project_name}-rag-api-logs"
  }
}





