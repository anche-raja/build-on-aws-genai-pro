# EventBridge Rules for Scheduled Tasks

# Scheduled Feedback Analysis Rule
resource "aws_cloudwatch_event_rule" "feedback_analysis" {
  name                = "${var.project_name}-feedback-analysis-${var.environment}"
  description         = "Trigger feedback analysis on schedule"
  schedule_expression = var.feedback_analysis_schedule

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-feedback-analysis-${var.environment}"
    }
  )
}

# Target for Feedback Analysis Rule
resource "aws_cloudwatch_event_target" "feedback_analysis" {
  rule      = aws_cloudwatch_event_rule.feedback_analysis.name
  target_id = "FeedbackAnalysisLambda"
  arn       = aws_lambda_function.analyze_feedback.arn

  input = jsonencode({
    time_range_hours = 24
    analysis_type    = "scheduled"
  })
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge_feedback" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analyze_feedback.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.feedback_analysis.arn
}

# EventBridge Rule for DynamoDB Streams (Feedback)
resource "aws_cloudwatch_event_rule" "feedback_stream" {
  name        = "${var.project_name}-feedback-stream-${var.environment}"
  description = "Process feedback from DynamoDB streams"

  event_pattern = jsonencode({
    source      = ["aws.dynamodb"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      eventSource = ["dynamodb.amazonaws.com"]
      eventName   = ["PutItem", "UpdateItem"]
      requestParameters = {
        tableName = [aws_dynamodb_table.feedback.name]
      }
    }
  })

  tags = var.tags
}

# Optional: Event Rule for Prompt Template Updates
resource "aws_cloudwatch_event_rule" "prompt_template_updated" {
  name        = "${var.project_name}-prompt-template-updated-${var.environment}"
  description = "Trigger when prompt templates are updated"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.prompt_templates.bucket]
      }
      object = {
        key = [{
          prefix = "prompts/"
        }]
      }
    }
  })

  is_enabled = false  # Enable when S3 EventBridge notifications are configured

  tags = var.tags
}

# Outputs
output "feedback_analysis_rule_arn" {
  description = "EventBridge feedback analysis rule ARN"
  value       = aws_cloudwatch_event_rule.feedback_analysis.arn
}



