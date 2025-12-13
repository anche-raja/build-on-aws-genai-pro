# Terraform State Configuration
# Uncomment and configure this block to use S3 backend for remote state

# terraform {
#   backend "s3" {
#     bucket         = "terraform-state-bucket"
#     key            = "genai-knowledge-assistant/terraform.tfstate"
#     region         = "us-east-1"
#     encrypt        = true
#     dynamodb_table = "terraform-state-lock"
#   }
# }

