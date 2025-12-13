# Phase 6: Monitoring and Evaluation Infrastructure

# User Feedback DynamoDB Table
resource "aws_dynamodb_table" "user_feedback" {
  name         = "${var.project_name}-user-feedback"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "feedback_id"
  range_key    = "timestamp"

  attribute {
    name = "feedback_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "request_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "rating"
    type = "N"
  }

  # GSI for querying by request_id
  global_secondary_index {
    name            = "RequestIndex"
    hash_key        = "request_id"
    projection_type = "ALL"
  }

  # GSI for querying by user_id
  global_secondary_index {
    name            = "UserFeedbackIndex"
    hash_key        = "user_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI for querying by rating
  global_secondary_index {
    name            = "RatingIndex"
    hash_key        = "rating"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-user-feedback"
  }
}

# Quality Metrics DynamoDB Table
resource "aws_dynamodb_table" "quality_metrics" {
  name         = "${var.project_name}-quality-metrics"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "metric_id"
  range_key    = "timestamp"

  attribute {
    name = "metric_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "metric_type"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  # GSI for querying by metric type
  global_secondary_index {
    name            = "MetricTypeIndex"
    hash_key        = "metric_type"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI for daily aggregations
  global_secondary_index {
    name            = "DailyMetricsIndex"
    hash_key        = "date"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-quality-metrics"
  }
}

# S3 Bucket for Analytics Data Export
resource "aws_s3_bucket" "analytics_exports" {
  bucket = "${var.project_name}-analytics-exports-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-analytics-exports"
  }
}

resource "aws_s3_bucket_versioning" "analytics_exports" {
  bucket = aws_s3_bucket.analytics_exports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "analytics_exports" {
  bucket = aws_s3_bucket.analytics_exports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "analytics_exports" {
  bucket = aws_s3_bucket.analytics_exports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for analytics exports
resource "aws_s3_bucket_lifecycle_configuration" "analytics_exports" {
  bucket = aws_s3_bucket.analytics_exports.id

  rule {
    id     = "archive-old-analytics"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# CloudWatch Log Group for Quality Metrics
resource "aws_cloudwatch_log_group" "quality_metrics" {
  name              = "/aws/quality/${var.project_name}"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-quality-logs"
  }
}

# SNS Topic for Quality Alerts
resource "aws_sns_topic" "quality_alerts" {
  name = "${var.project_name}-quality-alerts"

  tags = {
    Name = "${var.project_name}-quality-alerts"
  }
}

# CloudWatch Composite Alarm for System Health
resource "aws_cloudwatch_metric_alarm" "low_response_quality" {
  alarm_name          = "${var.project_name}-low-response-quality"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "AverageRating"
  namespace           = "GenAI/Quality"
  period              = "300"
  statistic           = "Average"
  threshold           = "3.0"
  alarm_description   = "Alert when average response quality drops below 3.0"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "${var.project_name}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "GenAI/Quality"
  period              = "300"
  statistic           = "Average"
  threshold           = "5.0"
  alarm_description   = "Alert when error rate exceeds 5%"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_latency_p99" {
  alarm_name          = "${var.project_name}-high-latency-p99"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "QueryLatency"
  namespace           = "GenAI/KnowledgeAssistant"
  period              = "300"
  extended_statistic  = "p99"
  threshold           = "5000"
  alarm_description   = "Alert when P99 latency exceeds 5 seconds"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "low_cache_hit_rate" {
  alarm_name          = "${var.project_name}-low-cache-hit-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CacheHitRate"
  namespace           = "GenAI/Performance"
  period              = "300"
  statistic           = "Average"
  threshold           = "20.0"
  alarm_description   = "Alert when cache hit rate drops below 20%"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_token_usage" {
  alarm_name          = "${var.project_name}-high-token-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "TotalTokens"
  namespace           = "GenAI/KnowledgeAssistant"
  period              = "3600"
  statistic           = "Sum"
  threshold           = "1000000"
  alarm_description   = "Alert when hourly token usage exceeds 1M"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_cost_per_query" {
  alarm_name          = "${var.project_name}-high-cost-per-query"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "QueryCost"
  namespace           = "GenAI/KnowledgeAssistant"
  period              = "300"
  statistic           = "Average"
  threshold           = "0.05"
  alarm_description   = "Alert when average cost per query exceeds $0.05"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

# EventBridge Rule for Daily Quality Report
resource "aws_cloudwatch_event_rule" "daily_quality_report" {
  name                = "${var.project_name}-daily-quality-report"
  description         = "Trigger daily quality report generation"
  schedule_expression = "cron(0 8 * * ? *)"

  tags = {
    Name = "${var.project_name}-daily-report"
  }
}

# EventBridge Rule for Weekly Analytics Export
resource "aws_cloudwatch_event_rule" "weekly_analytics_export" {
  name                = "${var.project_name}-weekly-analytics-export"
  description         = "Trigger weekly analytics export to S3"
  schedule_expression = "cron(0 0 ? * SUN *)"

  tags = {
    Name = "${var.project_name}-weekly-export"
  }
}

# Lambda for Quality Report Generation
resource "aws_lambda_function" "quality_reporter" {
  filename         = data.archive_file.query_handler.output_path
  function_name    = "${var.project_name}-quality-reporter"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "quality_reporter.handler"
  source_code_hash = data.archive_file.query_handler.output_base64sha256
  runtime          = "python3.10"
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      QUALITY_METRICS_TABLE = aws_dynamodb_table.quality_metrics.name
      USER_FEEDBACK_TABLE   = aws_dynamodb_table.user_feedback.name
      EVALUATION_TABLE      = aws_dynamodb_table.evaluation_table.name
      ANALYTICS_BUCKET      = aws_s3_bucket.analytics_exports.id
      SNS_TOPIC             = aws_sns_topic.quality_alerts.arn
    }
  }

  tags = {
    Name = "${var.project_name}-quality-reporter"
  }
}

resource "aws_cloudwatch_event_target" "quality_report_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_quality_report.name
  target_id = "QualityReportLambda"
  arn       = aws_lambda_function.quality_reporter.arn
}

resource "aws_lambda_permission" "allow_eventbridge_quality_report" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.quality_reporter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_quality_report.arn
}

# Lambda for Analytics Export
resource "aws_lambda_function" "analytics_exporter" {
  filename         = data.archive_file.query_handler.output_path
  function_name    = "${var.project_name}-analytics-exporter"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "analytics_exporter.handler"
  source_code_hash = data.archive_file.query_handler.output_base64sha256
  runtime          = "python3.10"
  timeout          = 600
  memory_size      = 1024

  environment {
    variables = {
      QUALITY_METRICS_TABLE = aws_dynamodb_table.quality_metrics.name
      USER_FEEDBACK_TABLE   = aws_dynamodb_table.user_feedback.name
      EVALUATION_TABLE      = aws_dynamodb_table.evaluation_table.name
      AUDIT_TRAIL_TABLE     = aws_dynamodb_table.audit_trail.name
      ANALYTICS_BUCKET      = aws_s3_bucket.analytics_exports.id
    }
  }

  tags = {
    Name = "${var.project_name}-analytics-exporter"
  }
}

resource "aws_cloudwatch_event_target" "analytics_export_lambda" {
  rule      = aws_cloudwatch_event_rule.weekly_analytics_export.name
  target_id = "AnalyticsExportLambda"
  arn       = aws_lambda_function.analytics_exporter.arn
}

resource "aws_lambda_permission" "allow_eventbridge_analytics_export" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analytics_exporter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_analytics_export.arn
}

# CloudWatch Dashboard for Quality Metrics
resource "aws_cloudwatch_dashboard" "quality" {
  dashboard_name = "${var.project_name}-quality"

  dashboard_body = jsonencode({
    widgets = [
      # User Satisfaction Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/Quality", "AverageRating", { stat = "Average", label = "Avg Rating" }],
            [".", "ThumbsUp", { stat = "Sum", label = "Thumbs Up" }],
            [".", "ThumbsDown", { stat = "Sum", label = "Thumbs Down" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "User Satisfaction"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 5
            }
          }
        }
      },

      # Response Quality Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/Quality", "RelevanceScore", { stat = "Average", label = "Relevance" }],
            [".", "CoherenceScore", { stat = "Average", label = "Coherence" }],
            [".", "CompletenessScore", { stat = "Average", label = "Completeness" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Response Quality Scores"
          period  = 300
        }
      },

      # Performance Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/KnowledgeAssistant", "QueryLatency", { stat = "Average", label = "Avg" }],
            ["...", { stat = "p50", label = "P50" }],
            ["...", { stat = "p95", label = "P95" }],
            ["...", { stat = "p99", label = "P99" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Query Latency (ms)"
          period  = 300
        }
      },

      # Error Rate
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/Quality", "ErrorRate", { stat = "Average", label = "Error Rate %" }],
            [".", "SuccessRate", { stat = "Average", label = "Success Rate %" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Success & Error Rates"
          period  = 300
        }
      },

      # Cache Performance
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/Performance", "CacheHitRate", { stat = "Average", label = "Hit Rate %" }],
            [".", "CacheHits", { stat = "Sum", label = "Hits" }],
            [".", "CacheMisses", { stat = "Sum", label = "Misses" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Cache Performance"
          period  = 300
        }
      },

      # Cost Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/KnowledgeAssistant", "QueryCost", { stat = "Sum", label = "Total Cost" }],
            ["...", { stat = "Average", label = "Avg Cost/Query" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Cost Metrics ($)"
          period  = 300
        }
      },

      # Model Usage Distribution
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/Models", "SimpleModelUsage", { stat = "Sum" }],
            [".", "StandardModelUsage", { stat = "Sum" }],
            [".", "AdvancedModelUsage", { stat = "Sum" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "Model Tier Usage"
          period  = 300
        }
      },

      # Recent Feedback
      {
        type = "log"
        properties = {
          query   = <<-EOT
            SOURCE '${aws_cloudwatch_log_group.quality_metrics.name}'
            | fields @timestamp, feedback_type, rating, comment
            | filter feedback_type = 'user_feedback'
            | sort @timestamp desc
            | limit 20
          EOT
          region  = var.aws_region
          title   = "Recent User Feedback"
          stacked = false
        }
      }
    ]
  })
}

