# Output values for the GenAI Knowledge Assistant Infrastructure

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_api_gateway_stage.genai_knowledge_assistant.invoke_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.genai_knowledge_assistant.id
}

output "document_bucket_name" {
  description = "S3 bucket name for document storage"
  value       = aws_s3_bucket.document_bucket.id
}

output "document_bucket_arn" {
  description = "S3 bucket ARN for document storage"
  value       = aws_s3_bucket.document_bucket.arn
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = aws_opensearch_domain.vector_search.endpoint
}

output "opensearch_domain_name" {
  description = "OpenSearch domain name"
  value       = aws_opensearch_domain.vector_search.domain_name
}

output "opensearch_dashboard_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = aws_opensearch_domain.vector_search.dashboard_endpoint
}

output "opensearch_password_secret_arn" {
  description = "ARN of the secret containing OpenSearch credentials"
  value       = aws_secretsmanager_secret.opensearch_password.arn
  sensitive   = true
}

output "metadata_table_name" {
  description = "DynamoDB metadata table name"
  value       = aws_dynamodb_table.metadata_table.name
}

output "metadata_table_arn" {
  description = "DynamoDB metadata table ARN"
  value       = aws_dynamodb_table.metadata_table.arn
}

output "conversation_table_name" {
  description = "DynamoDB conversation table name"
  value       = aws_dynamodb_table.conversation_table.name
}

output "conversation_table_arn" {
  description = "DynamoDB conversation table ARN"
  value       = aws_dynamodb_table.conversation_table.arn
}

output "evaluation_table_name" {
  description = "DynamoDB evaluation table name"
  value       = aws_dynamodb_table.evaluation_table.name
}

output "evaluation_table_arn" {
  description = "DynamoDB evaluation table ARN"
  value       = aws_dynamodb_table.evaluation_table.arn
}

output "document_processor_function_name" {
  description = "Document processor Lambda function name"
  value       = aws_lambda_function.document_processor.function_name
}

output "document_processor_function_arn" {
  description = "Document processor Lambda function ARN"
  value       = aws_lambda_function.document_processor.arn
}

output "query_handler_function_name" {
  description = "Query handler Lambda function name"
  value       = aws_lambda_function.query_handler.function_name
}

output "query_handler_function_arn" {
  description = "Query handler Lambda function ARN"
  value       = aws_lambda_function.query_handler.arn
}

output "lambda_execution_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "cloudwatch_dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.genai_knowledge_assistant.dashboard_name
}

output "api_endpoints" {
  description = "API endpoint URLs"
  value = {
    documents = "${aws_api_gateway_stage.genai_knowledge_assistant.invoke_url}/documents"
    query     = "${aws_api_gateway_stage.genai_knowledge_assistant.invoke_url}/query"
  }
}

