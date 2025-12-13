# DynamoDB Table for Document Metadata
resource "aws_dynamodb_table" "metadata" {
  name         = var.metadata_table_name
  billing_mode = "PAY_PER_REQUEST"
  
  hash_key  = "document_id"
  range_key = "chunk_id"
  
  attribute {
    name = "document_id"
    type = "S"
  }
  
  attribute {
    name = "chunk_id"
    type = "S"
  }
  
  attribute {
    name = "document_type"
    type = "S"
  }
  
  attribute {
    name = "last_updated"
    type = "S"
  }
  
  attribute {
    name = "source"
    type = "S"
  }
  
  # GSI for querying by document type
  global_secondary_index {
    name            = "DocumentTypeIndex"
    hash_key        = "document_type"
    range_key       = "last_updated"
    projection_type = "ALL"
  }
  
  # GSI for querying by source
  global_secondary_index {
    name            = "SourceIndex"
    hash_key        = "source"
    range_key       = "last_updated"
    projection_type = "ALL"
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Name = "${var.project_name}-metadata"
  }
}

# DynamoDB Table for Feedback
resource "aws_dynamodb_table" "feedback" {
  name         = "${var.project_name}-feedback"
  billing_mode = "PAY_PER_REQUEST"
  
  hash_key  = "feedback_id"
  range_key = "timestamp"
  
  attribute {
    name = "feedback_id"
    type = "S"
  }
  
  attribute {
    name = "timestamp"
    type = "S"
  }
  
  attribute {
    name = "rating"
    type = "N"
  }
  
  # GSI for querying by rating
  global_secondary_index {
    name            = "RatingIndex"
    hash_key        = "rating"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Name = "${var.project_name}-feedback"
  }
}




