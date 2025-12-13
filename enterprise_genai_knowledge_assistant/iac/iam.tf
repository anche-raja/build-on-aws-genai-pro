# IAM Role for API Gateway CloudWatch Logging
resource "aws_iam_role" "api_gateway_cloudwatch_role" {
  name = "${var.project_name}-api-gateway-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-api-gateway-cloudwatch-role"
  }
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch_policy" {
  role       = aws_iam_role.api_gateway_cloudwatch_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Set API Gateway account-level CloudWatch role
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_role.arn
}

# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-lambda-role"
  }
}

# Attach AWS managed policy for Lambda basic execution
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy for Bedrock access
resource "aws_iam_role_policy" "bedrock_policy" {
  name = "${var.project_name}-bedrock-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ApplyGuardrail"
        ]
        Resource = "*"
      }
    ]
  })
}

# Custom policy for S3, DynamoDB, OpenSearch, and Comprehend access
resource "aws_iam_role_policy" "services_policy" {
  name = "${var.project_name}-services-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.document_bucket.arn,
          "${aws_s3_bucket.document_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.metadata_table.arn,
          aws_dynamodb_table.conversation_table.arn,
          aws_dynamodb_table.evaluation_table.arn,
          aws_dynamodb_table.audit_trail.arn,
          "${aws_dynamodb_table.audit_trail.arn}/index/*",
          aws_dynamodb_table.user_feedback.arn,
          "${aws_dynamodb_table.user_feedback.arn}/index/*",
          aws_dynamodb_table.quality_metrics.arn,
          "${aws_dynamodb_table.quality_metrics.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete"
        ]
        Resource = "${aws_opensearch_domain.vector_search.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "comprehend:DetectPiiEntities",
          "comprehend:DetectSentiment",
          "comprehend:DetectEntities"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.opensearch_password.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "${aws_cloudwatch_log_group.governance.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.compliance_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.audit_logs.arn}/*",
          "${aws_s3_bucket.analytics_exports.arn}/*"
        ]
      }
    ]
  })
}

