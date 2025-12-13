# Terraform Outputs

# API Gateway Outputs
output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}/query"
}

output "feedback_api_url" {
  description = "Feedback API endpoint URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}/feedback"
}

# Step Functions Outputs
output "workflow_arn" {
  description = "Step Functions workflow ARN"
  value       = aws_sfn_state_machine.customer_support_workflow.arn
}

output "workflow_console_url" {
  description = "Step Functions console URL"
  value       = "https://console.aws.amazon.com/states/home?region=${var.aws_region}#/statemachines/view/${aws_sfn_state_machine.customer_support_workflow.arn}"
}

# DynamoDB Outputs
output "conversations_table" {
  description = "Conversations DynamoDB table name"
  value       = aws_dynamodb_table.conversations.name
}

output "prompts_table" {
  description = "Prompts DynamoDB table name"
  value       = aws_dynamodb_table.prompts.name
}

output "feedback_table" {
  description = "Feedback DynamoDB table name"
  value       = aws_dynamodb_table.feedback.name
}

# S3 Outputs
output "prompt_templates_bucket" {
  description = "Prompt templates S3 bucket name"
  value       = aws_s3_bucket.prompt_templates.bucket
}

# Lambda Outputs
output "lambda_functions" {
  description = "Lambda function names"
  value = {
    capture_query    = aws_lambda_function.capture_query.function_name
    detect_intent    = aws_lambda_function.detect_intent.function_name
    generate_response = aws_lambda_function.generate_response.function_name
    validate_quality = aws_lambda_function.validate_quality.function_name
    collect_feedback = aws_lambda_function.collect_feedback.function_name
    analyze_feedback = aws_lambda_function.analyze_feedback.function_name
  }
}

# CloudWatch Outputs
output "cloudwatch_dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "log_groups" {
  description = "CloudWatch log group names"
  value = {
    api_gateway   = aws_cloudwatch_log_group.api_gateway.name
    step_functions = aws_cloudwatch_log_group.step_functions.name
    lambda_capture = aws_cloudwatch_log_group.capture_query.name
    lambda_intent  = aws_cloudwatch_log_group.detect_intent.name
    lambda_generate = aws_cloudwatch_log_group.generate_response.name
    lambda_quality = aws_cloudwatch_log_group.validate_quality.name
    lambda_feedback = aws_cloudwatch_log_group.collect_feedback.name
  }
}

# Test Command Output
output "test_command" {
  description = "Example curl command to test the API"
  value = <<-EOT
    curl -X POST ${aws_api_gateway_stage.main.invoke_url}/query \
      -H "Content-Type: application/json" \
      -d '{
        "query": "My EC2 instance is not responding to SSH connections",
        "user_id": "test-user-123"
      }'
  EOT
}

# Project Information
output "project_info" {
  description = "Project deployment information"
  value = {
    project_name = var.project_name
    environment  = var.environment
    region       = var.aws_region
    model_id     = var.bedrock_model_id
  }
}



