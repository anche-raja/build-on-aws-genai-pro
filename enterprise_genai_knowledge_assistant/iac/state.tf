# Terraform State Configuration
terraform {
  backend "s3" {
    bucket         = "ai-assistant-tf-state-123456" # Replace with a unique bucket name
    key            = "gka/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

