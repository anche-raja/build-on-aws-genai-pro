# CloudWatch Monitoring and Dashboards

# Custom CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsFailed", { stat = "Sum", label = "Failed Executions" }],
            [".", "ExecutionsSucceeded", { stat = "Sum", label = "Successful Executions" }],
            [".", "ExecutionTime", { stat = "Average", label = "Avg Execution Time (ms)" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Step Functions - Executions"
          yAxis = {
            left = {
              label = "Count"
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum" }],
            [".", "Errors", { stat = "Sum" }],
            [".", "Throttles", { stat = "Sum" }],
            [".", "Duration", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Functions - Overview"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["CustomerSupportAI", "FeedbackCount", { stat = "Sum" }],
            [".", "UserRating", { stat = "Average" }]
          ]
          period = 3600
          stat   = "Average"
          region = var.aws_region
          title  = "User Feedback Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", { stat = "Sum", label = "API Calls" }],
            [".", "4XXError", { stat = "Sum", label = "Client Errors" }],
            [".", "5XXError", { stat = "Sum", label = "Server Errors" }],
            [".", "Latency", { stat = "Average", label = "Latency (ms)" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "API Gateway - Performance"
        }
      },
      {
        type = "log"
        properties = {
          query   = "SOURCE '/aws/lambda/${var.project_name}-*' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "Recent Lambda Errors"
          stacked = false
        }
      }
    ]
  })
}

# CloudWatch Alarms

# Lambda Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  alarm_name          = "${var.project_name}-lambda-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when Lambda error rate is high"
  treat_missing_data  = "notBreaching"

  tags = var.tags
}

# API Gateway 4XX Error Alarm
resource "aws_cloudwatch_metric_alarm" "api_4xx_errors" {
  alarm_name          = "${var.project_name}-api-4xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "50"
  alarm_description   = "Alert when API Gateway client errors are high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.customer_support.name
  }

  tags = var.tags
}

# API Gateway 5XX Error Alarm
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  alarm_name          = "${var.project_name}-api-5xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when API Gateway server errors occur"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.customer_support.name
  }

  tags = var.tags
}

# DynamoDB Read Throttle Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttle" {
  alarm_name          = "${var.project_name}-dynamodb-read-throttle-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when DynamoDB read throttling occurs"
  treat_missing_data  = "notBreaching"

  tags = var.tags
}

# DynamoDB Write Throttle Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttle" {
  alarm_name          = "${var.project_name}-dynamodb-write-throttle-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when DynamoDB write throttling occurs"
  treat_missing_data  = "notBreaching"

  tags = var.tags
}

# CloudWatch Insights Query Definitions
resource "aws_cloudwatch_query_definition" "lambda_errors" {
  name = "${var.project_name}-lambda-errors-${var.environment}"

  log_group_names = [
    aws_cloudwatch_log_group.capture_query.name,
    aws_cloudwatch_log_group.detect_intent.name,
    aws_cloudwatch_log_group.generate_response.name,
    aws_cloudwatch_log_group.validate_quality.name,
    aws_cloudwatch_log_group.collect_feedback.name
  ]

  query_string = <<-QUERY
    fields @timestamp, @message, @logStream
    | filter @message like /ERROR/
    | sort @timestamp desc
    | limit 100
  QUERY
}

resource "aws_cloudwatch_query_definition" "intent_confidence" {
  name = "${var.project_name}-intent-confidence-${var.environment}"

  log_group_names = [
    aws_cloudwatch_log_group.detect_intent.name
  ]

  query_string = <<-QUERY
    fields @timestamp, @message
    | filter @message like /Intent detected/
    | parse @message "confidence: *)" as confidence
    | stats avg(confidence) as avg_confidence by bin(5m)
  QUERY
}

resource "aws_cloudwatch_query_definition" "quality_scores" {
  name = "${var.project_name}-quality-scores-${var.environment}"

  log_group_names = [
    aws_cloudwatch_log_group.validate_quality.name
  ]

  query_string = <<-QUERY
    fields @timestamp, @message
    | filter @message like /Quality validation score/
    | parse @message "score: *" as quality_score
    | stats avg(quality_score) as avg_quality, min(quality_score) as min_quality, max(quality_score) as max_quality by bin(5m)
  QUERY
}

# Outputs
output "dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}


