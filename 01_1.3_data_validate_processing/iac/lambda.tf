locals {
  lambda_function_name  = "TextValidationFunction"
  lambda_source_path    = "${path.module}/../lambda_custom_text_validation.py"
  lambda_package_output = "${path.module}/lambda_custom_text_validation.zip"
}

data "archive_file" "text_validation_lambda" {
  type        = "zip"
  source_file = local.lambda_source_path
  output_path = local.lambda_package_output
}

resource "aws_iam_role" "lambda_execution_role" {
  name = "text-validation-lambda-role"

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

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "text-validation-lambda-policy"
  role = aws_iam_role.lambda_execution_role.id

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
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_bucket_name}",
          "arn:aws:s3:::${var.project_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "text_validation" {
  function_name = local.lambda_function_name
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "lambda_custom_text_validation.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.text_validation_lambda.output_path
  source_code_hash = data.archive_file.text_validation_lambda.output_base64sha256

  timeout = 30

  environment {
    variables = {
      CLOUDWATCH_NAMESPACE = "CustomerFeedback/TextQuality"
      METRIC_SOURCE        = "TextReviews"
    }
  }
}

resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.text_validation.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.customer_feedback.arn
}

resource "aws_s3_bucket_notification" "text_validation_trigger" {
  bucket = aws_s3_bucket.customer_feedback.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.text_validation.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw-data/"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

