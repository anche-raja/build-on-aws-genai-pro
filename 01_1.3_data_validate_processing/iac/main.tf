terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.5"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "project_bucket_name" {
  description = "Unique S3 bucket name for customer feedback data"
  type        = string
  default     = "customer-feedback-analysis-ars"
}

locals {
  raw_data_key = "raw-data/customer_feedback.csv"
}

resource "aws_s3_bucket" "customer_feedback" {
  bucket = var.project_bucket_name
}

resource "aws_s3_bucket_versioning" "customer_feedback" {
  bucket = aws_s3_bucket.customer_feedback.id

  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_public_access_block" "customer_feedback" {
  bucket = aws_s3_bucket.customer_feedback.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "raw_customer_feedback" {
  bucket = aws_s3_bucket.customer_feedback.id
  key    = local.raw_data_key
  source = "${path.module}/../sample-data/customer_feedback.csv"
  etag   = filemd5("${path.module}/../sample-data/customer_feedback.csv")
}

resource "aws_iam_role" "glue_service_role" {
  name = "AWSGlueServiceRole-CustomerFeedback"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service_role_policy" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_policy" "s3_access_policy" {
  name        = "GlueS3AccessPolicy"
  description = "Policy for Glue to access S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_bucket_name}",
          "arn:aws:s3:::${var.project_bucket_name}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_access_attachment" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}

resource "aws_glue_catalog_database" "customer_feedback_db" {
  name = "customer_feedback_db"
}

resource "aws_glue_crawler" "customer_feedback_crawler" {
  database_name = aws_glue_catalog_database.customer_feedback_db.name
  name          = "customer_feedback_crawler"
  role          = aws_iam_role.glue_service_role.arn

  s3_target {
    path = "s3://${var.project_bucket_name}/raw-data/"
  }
}

