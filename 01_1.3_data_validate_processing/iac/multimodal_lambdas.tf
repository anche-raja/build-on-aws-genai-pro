# ============================================================================
# Multimodal Data Processing Lambda Functions
# ============================================================================

# Text Processing Lambda
# ============================================================================

data "archive_file" "text_processing_lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda_text_processing.py"
  output_path = "${path.module}/lambda_text_processing.zip"
}

resource "aws_iam_role" "text_processing_role" {
  name = "text-processing-lambda-role"

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

resource "aws_iam_role_policy" "text_processing_policy" {
  name = "text-processing-lambda-policy"
  role = aws_iam_role.text_processing_role.id

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
          "comprehend:DetectEntities",
          "comprehend:DetectSentiment",
          "comprehend:DetectKeyPhrases"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "text_processing" {
  function_name = "TextProcessingFunction"
  role          = aws_iam_role.text_processing_role.arn
  handler       = "lambda_text_processing.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.text_processing_lambda.output_path
  source_code_hash = data.archive_file.text_processing_lambda.output_base64sha256

  timeout = 60

  environment {
    variables = {
      QUALITY_THRESHOLD = "0.7"
    }
  }
}

resource "aws_lambda_permission" "text_processing_s3_invoke" {
  statement_id  = "AllowExecutionFromS3TextProcessing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.text_processing.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.customer_feedback.arn
}

resource "aws_s3_bucket_notification" "text_processing_trigger" {
  bucket = aws_s3_bucket.customer_feedback.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.text_processing.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "validation-results/"
    filter_suffix       = "_validation.json"
  }

  depends_on = [
    aws_lambda_permission.text_processing_s3_invoke,
    aws_s3_bucket_notification.text_validation_trigger
  ]
}

# Image Processing Lambda
# ============================================================================

data "archive_file" "image_processing_lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda_image_processing.py"
  output_path = "${path.module}/lambda_image_processing.zip"
}

resource "aws_iam_role" "image_processing_role" {
  name = "image-processing-lambda-role"

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

resource "aws_iam_role_policy" "image_processing_policy" {
  name = "image-processing-lambda-policy"
  role = aws_iam_role.image_processing_role.id

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
          "textract:DetectDocumentText",
          "rekognition:DetectLabels",
          "rekognition:DetectText"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "image_processing" {
  function_name = "ImageProcessingFunction"
  role          = aws_iam_role.image_processing_role.arn
  handler       = "lambda_image_processing.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.image_processing_lambda.output_path
  source_code_hash = data.archive_file.image_processing_lambda.output_base64sha256

  timeout = 60

  environment {
    variables = {
      MIN_CONFIDENCE = "70"
    }
  }
}

resource "aws_lambda_permission" "image_processing_s3_invoke" {
  statement_id  = "AllowExecutionFromS3ImageProcessing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.image_processing.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.customer_feedback.arn
}

resource "aws_s3_bucket_notification" "image_processing_trigger" {
  bucket = aws_s3_bucket.customer_feedback.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.image_processing.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw-data/images/"
  }

  depends_on = [
    aws_lambda_permission.image_processing_s3_invoke,
    aws_s3_bucket_notification.text_processing_trigger
  ]
}

# Audio Processing Lambda (Starts Transcription)
# ============================================================================

data "archive_file" "audio_processing_lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda_audio_processing.py"
  output_path = "${path.module}/lambda_audio_processing.zip"
}

resource "aws_iam_role" "audio_processing_role" {
  name = "audio-processing-lambda-role"

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

resource "aws_iam_role_policy" "audio_processing_policy" {
  name = "audio-processing-lambda-policy"
  role = aws_iam_role.audio_processing_role.id

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
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "audio_processing" {
  function_name = "AudioProcessingFunction"
  role          = aws_iam_role.audio_processing_role.arn
  handler       = "lambda_audio_processing.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.audio_processing_lambda.output_path
  source_code_hash = data.archive_file.audio_processing_lambda.output_base64sha256

  timeout = 60
}

resource "aws_lambda_permission" "audio_processing_s3_invoke" {
  statement_id  = "AllowExecutionFromS3AudioProcessing"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.audio_processing.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.customer_feedback.arn
}

resource "aws_s3_bucket_notification" "audio_processing_trigger" {
  bucket = aws_s3_bucket.customer_feedback.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.audio_processing.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw-data/audio/"
  }

  depends_on = [
    aws_lambda_permission.audio_processing_s3_invoke,
    aws_s3_bucket_notification.image_processing_trigger
  ]
}

# Transcription Completion Lambda (Processes Completed Transcriptions)
# ============================================================================

data "archive_file" "transcription_completion_lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda_transcription_completion.py"
  output_path = "${path.module}/lambda_transcription_completion.zip"
}

resource "aws_iam_role" "transcription_completion_role" {
  name = "transcription-completion-lambda-role"

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

resource "aws_iam_role_policy" "transcription_completion_policy" {
  name = "transcription-completion-lambda-policy"
  role = aws_iam_role.transcription_completion_role.id

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
          "transcribe:GetTranscriptionJob"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "comprehend:DetectSentiment",
          "comprehend:DetectKeyPhrases"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "transcription_completion" {
  function_name = "TranscriptionCompletionFunction"
  role          = aws_iam_role.transcription_completion_role.arn
  handler       = "lambda_transcription_completion.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.transcription_completion_lambda.output_path
  source_code_hash = data.archive_file.transcription_completion_lambda.output_base64sha256

  timeout = 60
}

# EventBridge rule to trigger Lambda when Transcribe job completes
resource "aws_cloudwatch_event_rule" "transcribe_completion" {
  name        = "transcribe-job-completion"
  description = "Trigger when Transcribe job completes"

  event_pattern = jsonencode({
    source      = ["aws.transcribe"]
    detail-type = ["Transcribe Job State Change"]
    detail = {
      TranscriptionJobStatus = ["COMPLETED", "FAILED"]
    }
  })
}

resource "aws_cloudwatch_event_target" "transcription_completion_lambda" {
  rule      = aws_cloudwatch_event_rule.transcribe_completion.name
  target_id = "TranscriptionCompletionLambda"
  arn       = aws_lambda_function.transcription_completion.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transcription_completion.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.transcribe_completion.arn
}

# Outputs
# ============================================================================

output "text_processing_lambda_arn" {
  value = aws_lambda_function.text_processing.arn
}

output "image_processing_lambda_arn" {
  value = aws_lambda_function.image_processing.arn
}

output "audio_processing_lambda_arn" {
  value = aws_lambda_function.audio_processing.arn
}

output "transcription_completion_lambda_arn" {
  value = aws_lambda_function.transcription_completion.arn
}

