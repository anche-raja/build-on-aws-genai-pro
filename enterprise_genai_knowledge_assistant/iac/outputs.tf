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

# Phase 5: Governance Outputs
output "audit_trail_table_name" {
  description = "Audit trail DynamoDB table name"
  value       = aws_dynamodb_table.audit_trail.name
}

output "audit_logs_bucket_name" {
  description = "S3 bucket for audit log archives"
  value       = aws_s3_bucket.audit_logs.id
}

output "guardrail_id" {
  description = "Bedrock Guardrail ID"
  value       = aws_bedrock_guardrail.content_safety.guardrail_id
}

output "guardrail_arn" {
  description = "Bedrock Guardrail ARN"
  value       = aws_bedrock_guardrail.content_safety.guardrail_arn
}

output "compliance_alerts_topic" {
  description = "SNS topic for compliance alerts"
  value       = aws_sns_topic.compliance_alerts.arn
}

output "governance_dashboard_name" {
  description = "Governance CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.governance.dashboard_name
}

output "governance_log_group" {
  description = "CloudWatch log group for governance events"
  value       = aws_cloudwatch_log_group.governance.name
}

# Phase 6: Monitoring & Evaluation Outputs
output "user_feedback_table_name" {
  description = "User feedback DynamoDB table name"
  value       = aws_dynamodb_table.user_feedback.name
}

output "quality_metrics_table_name" {
  description = "Quality metrics DynamoDB table name"
  value       = aws_dynamodb_table.quality_metrics.name
}

output "analytics_exports_bucket_name" {
  description = "S3 bucket for analytics exports"
  value       = aws_s3_bucket.analytics_exports.id
}

output "quality_alerts_topic" {
  description = "SNS topic for quality alerts"
  value       = aws_sns_topic.quality_alerts.arn
}

output "quality_dashboard_name" {
  description = "Quality CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.quality.dashboard_name
}

output "quality_log_group" {
  description = "CloudWatch log group for quality metrics"
  value       = aws_cloudwatch_log_group.quality_metrics.name
}

output "feedback_endpoint" {
  description = "API endpoint for user feedback"
  value       = "${aws_api_gateway_stage.genai_knowledge_assistant.invoke_url}/feedback"
}

