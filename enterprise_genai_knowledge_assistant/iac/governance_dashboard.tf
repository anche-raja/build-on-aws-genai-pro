# Phase 5: Governance Dashboard

resource "aws_cloudwatch_dashboard" "governance" {
  dashboard_name = "${var.project_name}-governance"

  dashboard_body = jsonencode({
    widgets = [
      # PII Detection Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/Governance", "PIIDetected", { stat = "Sum", label = "PII Detected" }],
            [".", "GuardrailBlocked", { stat = "Sum", label = "Content Blocked" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Safety & Compliance Events"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      
      # Query Safety Status
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/Governance", "PIIDetected", { stat = "Sum", label = "Queries with PII" }],
            ["AWS/Lambda", "Invocations", { stat = "Sum", label = "Total Queries" }]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Safety Statistics (Last Hour)"
          period  = 3600
        }
      },
      
      # Model Usage by Tier
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/KnowledgeAssistant", "QueryCost", { stat = "Sum", label = "Total Cost" }],
            [".", "QueryLatency", { stat = "Average", label = "Avg Latency" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Cost & Performance"
          period  = 300
        }
      },
      
      # Token Usage
      {
        type = "metric"
        properties = {
          metrics = [
            ["GenAI/KnowledgeAssistant", "PromptTokens", { stat = "Sum", label = "Input Tokens" }],
            [".", "ResponseTokens", { stat = "Sum", label = "Output Tokens" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "Token Usage"
          period  = 300
        }
      },
      
      # Audit Trail Events
      {
        type = "log"
        properties = {
          query   = <<-EOT
            SOURCE '${aws_cloudwatch_log_group.governance.name}'
            | fields @timestamp, event_type, severity, user_id
            | filter severity = 'HIGH' or severity = 'CRITICAL'
            | sort @timestamp desc
            | limit 50
          EOT
          region  = var.aws_region
          title   = "High Severity Governance Events"
          stacked = false
        }
      },
      
      # PII Detection Details
      {
        type = "log"
        properties = {
          query   = <<-EOT
            SOURCE '${aws_cloudwatch_log_group.governance.name}'
            | fields @timestamp, event_type, details
            | filter event_type = 'PII_DETECTED'
            | sort @timestamp desc
            | limit 20
          EOT
          region  = var.aws_region
          title   = "Recent PII Detections"
          stacked = false
        }
      },
      
      # Guardrail Interventions
      {
        type = "log"
        properties = {
          query   = <<-EOT
            SOURCE '${aws_cloudwatch_log_group.governance.name}'
            | fields @timestamp, event_type, details
            | filter event_type = 'CONTENT_BLOCKED' or event_type = 'RESPONSE_BLOCKED'
            | sort @timestamp desc
            | limit 20
          EOT
          region  = var.aws_region
          title   = "Guardrail Interventions"
          stacked = false
        }
      },
      
      # User Activity
      {
        type = "log"
        properties = {
          query   = <<-EOT
            SOURCE '${aws_cloudwatch_log_group.governance.name}'
            | fields @timestamp, user_id, event_type
            | stats count() by user_id
            | sort count() desc
            | limit 10
          EOT
          region  = var.aws_region
          title   = "Top Users by Activity"
          stacked = false
        }
      },
      
      # Compliance Summary
      {
        type = "log"
        properties = {
          query   = <<-EOT
            SOURCE '${aws_cloudwatch_log_group.governance.name}'
            | fields event_type
            | stats count() by event_type
            | sort count() desc
          EOT
          region  = var.aws_region
          title   = "Events by Type"
          stacked = false
        }
      }
    ]
  })
}

# EventBridge Rule for Daily Audit Export
resource "aws_cloudwatch_event_rule" "daily_audit_export" {
  name                = "${var.project_name}-daily-audit-export"
  description         = "Trigger daily audit log export to S3"
  schedule_expression = "cron(0 2 * * ? *)"  # 2 AM UTC daily

  tags = {
    Name = "${var.project_name}-audit-export"
  }
}

# Lambda for Audit Export (placeholder - would need implementation)
resource "aws_lambda_function" "audit_exporter" {
  filename         = data.archive_file.query_handler.output_path  # Reuse for now
  function_name    = "${var.project_name}-audit-exporter"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "governance_handler.export_handler"
  source_code_hash = data.archive_file.query_handler.output_base64sha256
  runtime          = "python3.10"
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      AUDIT_TRAIL_TABLE = aws_dynamodb_table.audit_trail.name
      AUDIT_LOGS_BUCKET = aws_s3_bucket.audit_logs.id
    }
  }

  tags = {
    Name = "${var.project_name}-audit-exporter"
  }
}

resource "aws_cloudwatch_event_target" "audit_export_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_audit_export.name
  target_id = "AuditExportLambda"
  arn       = aws_lambda_function.audit_exporter.arn
}

resource "aws_lambda_permission" "allow_eventbridge_audit_export" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.audit_exporter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_audit_export.arn
}

