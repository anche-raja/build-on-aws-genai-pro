# Step Functions State Machine for Customer Support AI Assistant

# Read the workflow definition
locals {
  workflow_definition = templatefile("${path.module}/../step_functions_workflow.json", {
    CaptureQueryFunctionArn    = aws_lambda_function.capture_query.arn
    DetectIntentFunctionArn    = aws_lambda_function.detect_intent.arn
    GenerateResponseFunctionArn = aws_lambda_function.generate_response.arn
    ValidateQualityFunctionArn = aws_lambda_function.validate_quality.arn
    CollectFeedbackFunctionArn = aws_lambda_function.collect_feedback.arn
  })
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "customer_support_workflow" {
  name     = "${var.project_name}-workflow-${var.environment}"
  role_arn = aws_iam_role.step_functions_execution.arn

  definition = local.workflow_definition

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = var.enable_xray
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-workflow-${var.environment}"
      Type = "StateMachine"
    }
  )
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.project_name}-workflow-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = var.tags
}

# CloudWatch Alarms for Step Functions

# Execution Failed Alarm
resource "aws_cloudwatch_metric_alarm" "execution_failed" {
  alarm_name          = "${var.project_name}-workflow-execution-failed-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Step Functions executions fail"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.customer_support_workflow.arn
  }

  tags = var.tags
}

# Execution Duration Alarm
resource "aws_cloudwatch_metric_alarm" "execution_duration" {
  alarm_name          = "${var.project_name}-workflow-execution-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Average"
  threshold           = "30000"  # 30 seconds
  alarm_description   = "Alert when Step Functions execution time is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.customer_support_workflow.arn
  }

  tags = var.tags
}

# Execution Throttled Alarm
resource "aws_cloudwatch_metric_alarm" "execution_throttled" {
  alarm_name          = "${var.project_name}-workflow-execution-throttled-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionThrottled"
  namespace           = "AWS/States"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when Step Functions executions are throttled"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.customer_support_workflow.arn
  }

  tags = var.tags
}

# Outputs
output "state_machine_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.customer_support_workflow.arn
}

output "state_machine_name" {
  description = "Step Functions state machine name"
  value       = aws_sfn_state_machine.customer_support_workflow.name
}



