# OpenSearch Domain for Vector Search
resource "aws_opensearch_domain" "vector_search" {
  domain_name    = "${var.project_name}-domain"
  engine_version = "OpenSearch_2.11"
  
  cluster_config {
    instance_type          = var.opensearch_instance_type
    instance_count         = var.opensearch_instance_count
    zone_awareness_enabled = true
    
    zone_awareness_config {
      availability_zone_count = 3
    }
  }
  
  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.opensearch_ebs_volume_size
  }
  
  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
    "plugins.ml_commons.only_run_on_ml_node" = "false"
  }
  
  encrypt_at_rest {
    enabled = true
  }
  
  node_to_node_encryption {
    enabled = true
  }
  
  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }
  
  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    
    master_user_options {
      master_user_name     = "admin"
      master_user_password = random_password.opensearch_master.result
    }
  }
  
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_execution.arn
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-domain/*"
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-opensearch"
  }
}

# Random password for OpenSearch master user
resource "random_password" "opensearch_master" {
  length  = 16
  special = true
}

# Store password in Secrets Manager
resource "aws_secretsmanager_secret" "opensearch_credentials" {
  name = "${var.project_name}-opensearch-credentials"
  
  tags = {
    Name = "${var.project_name}-opensearch-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "opensearch_credentials" {
  secret_id = aws_secretsmanager_secret.opensearch_credentials.id
  
  secret_string = jsonencode({
    username = "admin"
    password = random_password.opensearch_master.result
    endpoint = aws_opensearch_domain.vector_search.endpoint
  })
}

# Data source for current account
data "aws_caller_identity" "current" {}





