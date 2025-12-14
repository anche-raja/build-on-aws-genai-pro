# OpenSearch Domain for vector search
resource "aws_opensearch_domain" "vector_search" {
  domain_name    = var.project_name
  engine_version = "OpenSearch_2.5"

  cluster_config {
    instance_type  = var.opensearch_instance_type
    instance_count = var.opensearch_data_nodes
  }

  ebs_options {
    ebs_enabled = true
    volume_size = var.opensearch_ebs_volume_size
    volume_type = "gp3"
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
      master_user_password = random_password.opensearch_master_password.result
    }
    # Allow IAM role-based access for Lambda
    anonymous_auth_enabled = false
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_execution_role.arn
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}/*"
      },
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = [
          "es:ESHttp*"
        ]
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}/*"
        Condition = {
          IpAddress = {
            "aws:SourceIp" = ["0.0.0.0/0"]
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-vector-search"
  }
}

# Random password for OpenSearch master user
# Must contain: uppercase, lowercase, number, special character
resource "random_password" "opensearch_master_password" {
  length           = 16
  special          = true
  override_special = "!@#$%^&*"
  min_upper        = 1
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
}

# Store OpenSearch password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "opensearch_password" {
  name                    = "${var.project_name}-opensearch-password"
  recovery_window_in_days = 0  # Force immediate deletion to allow recreation
  
  lifecycle {
    create_before_destroy = false
  }
}

resource "aws_secretsmanager_secret_version" "opensearch_password" {
  secret_id = aws_secretsmanager_secret.opensearch_password.id
  secret_string = jsonencode({
    username = "admin"
    password = random_password.opensearch_master_password.result
  })
}

# Automatically configure OpenSearch role mapping for Lambda
resource "null_resource" "configure_opensearch_role_mapping" {
  depends_on = [
    aws_opensearch_domain.vector_search,
    aws_secretsmanager_secret_version.opensearch_password
  ]

  triggers = {
    # Rerun if Lambda role changes
    lambda_role_arn = aws_iam_role.lambda_execution_role.arn
    # Rerun if OpenSearch endpoint changes
    opensearch_endpoint = aws_opensearch_domain.vector_search.endpoint
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      
      # Wait for OpenSearch to be fully ready
      echo "Waiting for OpenSearch to be ready..."
      sleep 30
      
      # Get credentials
      USERNAME="admin"
      PASSWORD="${random_password.opensearch_master_password.result}"
      OPENSEARCH_ENDPOINT="${aws_opensearch_domain.vector_search.endpoint}"
      LAMBDA_ROLE_ARN="${aws_iam_role.lambda_execution_role.arn}"
      
      # Configure role mapping
      echo "Configuring OpenSearch role mapping for Lambda..."
      curl -s -u "$USERNAME:$PASSWORD" \
        -X PUT "https://$OPENSEARCH_ENDPOINT/_plugins/_security/api/rolesmapping/all_access" \
        -H 'Content-Type: application/json' \
        -d '{
          "backend_roles": ["'"$LAMBDA_ROLE_ARN"'"],
          "hosts": [],
          "users": []
        }' || echo "Role mapping may already exist or will be configured on next apply"
      
      echo "✅ OpenSearch role mapping configured"
    EOT
  }
}

