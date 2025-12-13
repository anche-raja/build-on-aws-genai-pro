# Terraform Variables for Customer Support AI Assistant

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "customer-support-ai"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID to use"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "bedrock_guardrail_id" {
  description = "Amazon Bedrock Guardrail ID (optional)"
  type        = string
  default     = ""
}

variable "quality_threshold" {
  description = "Quality validation threshold (0-100)"
  type        = number
  default     = 70
}

variable "conversation_ttl_hours" {
  description = "TTL for conversation sessions in hours"
  type        = number
  default     = 24
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "enable_cloudtrail" {
  description = "Enable CloudTrail for audit logging"
  type        = bool
  default     = true
}

variable "enable_xray" {
  description = "Enable AWS X-Ray for tracing"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "CustomerSupportAI"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}

# API Gateway variables
variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 100
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 50
}

# Monitoring variables
variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 7
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

# EventBridge variables
variable "feedback_analysis_schedule" {
  description = "Schedule expression for feedback analysis (cron)"
  type        = string
  default     = "rate(1 hour)"
}


