# Amazon Bedrock Guardrails for Content Safety

resource "aws_bedrock_guardrail" "content_safety" {
  name                      = "${var.project_name}-content-safety"
  description              = "Content safety guardrail for GenAI Knowledge Assistant"
  blocked_input_messaging  = "I cannot process this request as it contains inappropriate content."
  blocked_outputs_messaging = "I cannot provide this response due to content safety policies."

  # Content Policy - Block harmful content
  content_policy_config {
    # Sexual content
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "SEXUAL"
    }

    # Violence
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "VIOLENCE"
    }

    # Hate speech
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "HATE"
    }

    # Insults
    filters_config {
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
      type            = "INSULTS"
    }

    # Misconduct
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type            = "MISCONDUCT"
    }

    # Prompt attacks
    filters_config {
      input_strength  = "HIGH"
      output_strength = "NONE"
      type            = "PROMPT_ATTACK"
    }
  }

  # Sensitive Information Policy - PII protection
  sensitive_information_policy_config {
    # Email addresses - ANONYMIZE instead of BLOCK for resume content
    pii_entities_config {
      action = "ANONYMIZE"
      type   = "EMAIL"
    }

    # Phone numbers - ANONYMIZE instead of BLOCK for resume content
    pii_entities_config {
      action = "ANONYMIZE"
      type   = "PHONE"
    }

    # Social Security Numbers - Keep BLOCK (truly sensitive)
    pii_entities_config {
      action = "BLOCK"
      type   = "US_SOCIAL_SECURITY_NUMBER"
    }

    # Credit card numbers - Keep BLOCK (truly sensitive)
    pii_entities_config {
      action = "BLOCK"
      type   = "CREDIT_DEBIT_CARD_NUMBER"
    }

    # Names
    pii_entities_config {
      action = "ANONYMIZE"
      type   = "NAME"
    }

    # Addresses
    pii_entities_config {
      action = "ANONYMIZE"
      type   = "ADDRESS"
    }
  }

  # Topic Policy - Restrict certain topics
  topic_policy_config {
    topics_config {
      name       = "Financial Advice"
      definition = "Investment advice, stock recommendations, or financial planning guidance"
      examples   = ["Should I invest in stocks?", "What's the best investment strategy?"]
      type       = "DENY"
    }

    topics_config {
      name       = "Medical Advice"
      definition = "Medical diagnosis, treatment recommendations, or health guidance"
      examples   = ["Should I take this medication?", "How do I treat this condition?"]
      type       = "DENY"
    }

    topics_config {
      name       = "Legal Advice"
      definition = "Legal advice, case analysis, or representation guidance"
      examples   = ["Should I sue?", "How do I file a lawsuit?"]
      type       = "DENY"
    }
  }

  # Word Policy - Block specific terms
  word_policy_config {
    # Custom words/phrases to block
    words_config {
      text = "confidential"
    }

    words_config {
      text = "internal only"
    }

    # Regex patterns for sensitive data
    managed_word_lists_config {
      type = "PROFANITY"
    }
  }

  tags = {
    Name        = "${var.project_name}-guardrail"
    Environment = "production"
  }
}

# Audit Trail Table for Governance
resource "aws_dynamodb_table" "audit_trail" {
  name         = "${var.project_name}-audit-trail"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "audit_id"
  range_key    = "timestamp"

  attribute {
    name = "audit_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "event_type"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  # GSI for querying by event type
  global_secondary_index {
    name            = "EventTypeIndex"
    hash_key        = "event_type"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI for querying by user
  global_secondary_index {
    name            = "UserIndex"
    hash_key        = "user_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # TTL for audit logs (7 years for compliance)
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
    Name       = "${var.project_name}-audit-trail"
    Compliance = "SOC2-HIPAA-GDPR"
  }
}

# S3 Bucket for Audit Log Archive
resource "aws_s3_bucket" "audit_logs" {
  bucket = "${var.project_name}-audit-logs-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name       = "${var.project_name}-audit-logs"
    Compliance = "SOC2-HIPAA-GDPR"
  }
}

resource "aws_s3_bucket_versioning" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for audit logs
resource "aws_s3_bucket_lifecycle_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  rule {
    id     = "archive-old-logs"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555  # 7 years
    }
  }
}

# CloudWatch Log Group for Governance Events
resource "aws_cloudwatch_log_group" "governance" {
  name              = "/aws/governance/${var.project_name}"
  retention_in_days = 90  # 90 days in CloudWatch, then archived to S3

  tags = {
    Name = "${var.project_name}-governance-logs"
  }
}

# SNS Topic for Compliance Alerts
resource "aws_sns_topic" "compliance_alerts" {
  name = "${var.project_name}-compliance-alerts"

  tags = {
    Name = "${var.project_name}-compliance-alerts"
  }
}

# CloudWatch Alarms for Governance
resource "aws_cloudwatch_metric_alarm" "pii_detected" {
  alarm_name          = "${var.project_name}-pii-detected"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "PIIDetected"
  namespace           = "GenAI/Governance"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when PII is detected in queries"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.compliance_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "guardrail_blocked" {
  alarm_name          = "${var.project_name}-guardrail-blocked"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "GuardrailBlocked"
  namespace           = "GenAI/Governance"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when guardrails block content frequently"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.compliance_alerts.arn]
}

