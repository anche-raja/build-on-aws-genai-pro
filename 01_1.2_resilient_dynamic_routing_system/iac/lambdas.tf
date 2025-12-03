# IAM Role and Policy (Shared)
resource "aws_iam_role" "lambda_role" {
  name = "ai_assistant_lambda_role"

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
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "ai_assistant_lambda_policy"
  description = "Policy for AI Assistant Lambda to access Bedrock and AppConfig"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "appconfig:GetConfiguration",
          "appconfig:GetLatestConfiguration",
          "appconfig:StartConfigurationSession"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# 1. Model Selector Lambda (Primary)
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../app/model_selector.py"
  output_path = "${path.module}/../app/model_selector.zip"
}

resource "aws_lambda_function" "ai_assistant_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "AIAssistantLambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "model_selector.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      APPCONFIG_APPLICATION = aws_appconfig_application.ai_assistant_app.name
      APPCONFIG_ENVIRONMENT = aws_appconfig_environment.production.name
      APPCONFIG_PROFILE     = aws_appconfig_configuration_profile.model_selection_strategy.name
    }
  }
}

output "lambda_function_arn" {
  value = aws_lambda_function.ai_assistant_lambda.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.ai_assistant_lambda.function_name
}

# 2. Fallback Lambda
data "archive_file" "fallback_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../app/fallback_handler.py"
  output_path = "${path.module}/../app/fallback_handler.zip"
}

resource "aws_lambda_function" "fallback_lambda" {
  filename         = data.archive_file.fallback_lambda_zip.output_path
  function_name    = "AIAssistantFallbackLambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "fallback_handler.lambda_handler"
  source_code_hash = data.archive_file.fallback_lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      # No AppConfig needed for fallback, hardcoded for reliability
    }
  }
}

output "fallback_lambda_function_arn" {
  value = aws_lambda_function.fallback_lambda.arn
}

# 3. Degradation Lambda
data "archive_file" "degradation_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../app/degradation_handler.py"
  output_path = "${path.module}/../app/degradation_handler.zip"
}

resource "aws_lambda_function" "degradation_lambda" {
  filename         = data.archive_file.degradation_lambda_zip.output_path
  function_name    = "AIAssistantDegradationLambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "degradation_handler.lambda_handler"
  source_code_hash = data.archive_file.degradation_lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 10

  environment {
    variables = {
      # No external dependencies needed
    }
  }
}

output "degradation_lambda_function_arn" {
  value = aws_lambda_function.degradation_lambda.arn
}

