variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "rag-vector-search"
}

# S3 Configuration
variable "document_bucket_name" {
  description = "S3 bucket name for documents"
  type        = string
}

# DynamoDB Configuration
variable "metadata_table_name" {
  description = "DynamoDB table name for metadata"
  type        = string
  default     = "DocumentMetadata"
}

# OpenSearch Configuration
variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "r6g.large.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
  default     = 3
}

variable "opensearch_ebs_volume_size" {
  description = "EBS volume size for OpenSearch (GB)"
  type        = number
  default     = 100
}

# Bedrock Configuration
variable "embedding_model_id" {
  description = "Bedrock embedding model ID"
  type        = string
  default     = "amazon.titan-embed-text-v1"
}

variable "foundation_model_id" {
  description = "Bedrock foundation model ID for generation"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

# Lambda Configuration
variable "lambda_memory_size" {
  description = "Memory size for Lambda functions (MB)"
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions (seconds)"
  type        = number
  default     = 300
}

# Sync Configuration
variable "max_age_days" {
  description = "Maximum age in days before document is considered stale"
  type        = number
  default     = 30
}

variable "sync_schedule_expression" {
  description = "EventBridge schedule expression for sync"
  type        = string
  default     = "rate(1 day)"
}

# VPC Configuration (optional)
variable "vpc_id" {
  description = "VPC ID for OpenSearch (optional)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for OpenSearch (optional)"
  type        = list(string)
  default     = []
}

