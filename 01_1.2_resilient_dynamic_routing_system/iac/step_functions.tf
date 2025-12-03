resource "aws_iam_role" "step_functions_role" {
  name = "ai_assistant_step_functions_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "step_functions_policy" {
  name = "ai_assistant_step_functions_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.ai_assistant_lambda.arn,
          aws_lambda_function.fallback_lambda.arn,
          aws_lambda_function.degradation_lambda.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_functions_policy_attach" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = aws_iam_policy.step_functions_policy.arn
}

# Create Log Group for Step Functions
resource "aws_cloudwatch_log_group" "sfn_log_group" {
  name              = "/aws/vendedlogs/states/AIAssistantWorkflow-Logs"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_resource_policy" "sfn_logging_policy" {
  policy_name = "SFNLoggingPolicy"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.sfn_log_group.arn}:*"
      }
    ]
  })
}

resource "aws_sfn_state_machine" "ai_assistant_workflow" {
  name     = "AIAssistantWorkflow"
  role_arn = aws_iam_role.step_functions_role.arn
  type     = "EXPRESS"

  definition = templatefile("${path.module}/step_functions_definition.json", {
    PrimaryModelLambdaArn  = aws_lambda_function.ai_assistant_lambda.arn
    FallbackModelLambdaArn = aws_lambda_function.fallback_lambda.arn
    DegradationLambdaArn   = aws_lambda_function.degradation_lambda.arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn_log_group.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  
  depends_on = [aws_cloudwatch_log_resource_policy.sfn_logging_policy]
}

output "step_functions_arn" {
  value = aws_sfn_state_machine.ai_assistant_workflow.arn
}
