output "s3_bucket_name" {
  description = "Name of the S3 bucket for documents"
  value       = aws_s3_bucket.documents.id
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB metadata table"
  value       = aws_dynamodb_table.metadata.name
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = aws_opensearch_domain.vector_search.endpoint
}

output "opensearch_dashboard_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = "${aws_opensearch_domain.vector_search.endpoint}/_dashboards"
}

output "api_gateway_url" {
  description = "API Gateway invocation URL"
  value       = "${aws_api_gateway_stage.rag_api.invoke_url}/query"
}

output "document_processor_lambda_arn" {
  description = "ARN of the document processor Lambda function"
  value       = aws_lambda_function.document_processor.arn
}

output "rag_api_lambda_arn" {
  description = "ARN of the RAG API Lambda function"
  value       = aws_lambda_function.rag_api.arn
}

output "sync_scheduler_lambda_arn" {
  description = "ARN of the sync scheduler Lambda function"
  value       = aws_lambda_function.sync_scheduler.arn
}

output "step_functions_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.sync_workflow.arn
}

output "opensearch_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret containing OpenSearch credentials"
  value       = aws_secretsmanager_secret.opensearch_credentials.arn
}

output "bedrock_kb_role_arn" {
  description = "ARN of the IAM role for Bedrock Knowledge Base"
  value       = aws_iam_role.bedrock_kb.arn
}




