# DynamoDB Tables for Customer Support AI Assistant

# Conversation History Table
resource "aws_dynamodb_table" "conversations" {
  name           = "${var.project_name}-conversations-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    range_key       = "created_at"
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

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-conversations-${var.environment}"
      Type = "ConversationHistory"
    }
  )
}

# Prompt Templates Metadata Table
resource "aws_dynamodb_table" "prompts" {
  name           = "${var.project_name}-prompts-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "template_id"
  range_key      = "version"

  attribute {
    name = "template_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "CreatedAtIndex"
    hash_key        = "template_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-prompts-${var.environment}"
      Type = "PromptMetadata"
    }
  )
}

# Feedback Table
resource "aws_dynamodb_table" "feedback" {
  name           = "${var.project_name}-feedback-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "feedback_id"

  attribute {
    name = "feedback_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "SessionIdIndex"
    hash_key        = "session_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "TimestampIndex"
    hash_key        = "timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-feedback-${var.environment}"
      Type = "Feedback"
    }
  )
}

# Outputs
output "conversations_table_name" {
  description = "Conversations DynamoDB table name"
  value       = aws_dynamodb_table.conversations.name
}

output "prompts_table_name" {
  description = "Prompts DynamoDB table name"
  value       = aws_dynamodb_table.prompts.name
}

output "feedback_table_name" {
  description = "Feedback DynamoDB table name"
  value       = aws_dynamodb_table.feedback.name
}

output "conversations_table_arn" {
  description = "Conversations DynamoDB table ARN"
  value       = aws_dynamodb_table.conversations.arn
}

output "prompts_table_arn" {
  description = "Prompts DynamoDB table ARN"
  value       = aws_dynamodb_table.prompts.arn
}

output "feedback_table_arn" {
  description = "Feedback DynamoDB table ARN"
  value       = aws_dynamodb_table.feedback.arn
}


