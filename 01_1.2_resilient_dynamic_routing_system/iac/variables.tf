variable "s3_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for Terraform state locking"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-assistant"
}

variable "force_destroy" {
  description = "Whether to allow destruction of the S3 bucket"
  type        = bool
  default     = false
}

variable "sse_kms_key_arn" {
  description = "ARN of the KMS key for server-side encryption"
  type        = string
  default     = ""
}

