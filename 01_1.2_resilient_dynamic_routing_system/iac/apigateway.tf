resource "aws_api_gateway_rest_api" "ai_assistant_api" {
  name        = "AIAssistantAPI"
  description = "API for AI Assistant"
}

resource "aws_api_gateway_resource" "generate" {
  rest_api_id = aws_api_gateway_rest_api.ai_assistant_api.id
  parent_id   = aws_api_gateway_rest_api.ai_assistant_api.root_resource_id
  path_part   = "generate"
}

resource "aws_api_gateway_method" "post_generate" {
  rest_api_id   = aws_api_gateway_rest_api.ai_assistant_api.id
  resource_id   = aws_api_gateway_resource.generate.id
  http_method   = "POST"
  authorization = "NONE"
}

# IAM Role for API Gateway to invoke Step Functions
resource "aws_iam_role" "api_gateway_step_functions_role" {
  name = "api_gateway_step_functions_role"

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
}

resource "aws_iam_policy" "api_gateway_step_functions_policy" {
  name = "api_gateway_step_functions_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "states:StartSyncExecution"
        Effect   = "Allow"
        Resource = aws_sfn_state_machine.ai_assistant_workflow.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_gateway_step_functions_attach" {
  role       = aws_iam_role.api_gateway_step_functions_role.name
  policy_arn = aws_iam_policy.api_gateway_step_functions_policy.arn
}

# Integration with Step Functions (Synchronous)
resource "aws_api_gateway_integration" "step_functions_integration" {
  rest_api_id             = aws_api_gateway_rest_api.ai_assistant_api.id
  resource_id             = aws_api_gateway_resource.generate.id
  http_method             = aws_api_gateway_method.post_generate.http_method
  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = "arn:aws:apigateway:${data.aws_region.current.name}:states:action/StartSyncExecution"
  credentials             = aws_iam_role.api_gateway_step_functions_role.arn

  request_templates = {
    "application/json" = <<EOF
{
    "input": "$util.escapeJavaScript($input.json('$'))",
    "stateMachineArn": "${aws_sfn_state_machine.ai_assistant_workflow.arn}"
}
EOF
  }
}

resource "aws_api_gateway_method_response" "response_200" {
  rest_api_id = aws_api_gateway_rest_api.ai_assistant_api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.post_generate.http_method
  status_code = "200"
  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "step_functions_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.ai_assistant_api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.post_generate.http_method
  status_code = aws_api_gateway_method_response.response_200.status_code

  # Map the Step Functions output to the response body
  response_templates = {
    "application/json" = <<EOF
#set($inputRoot = $input.path('$'))
$inputRoot.output
EOF
  }

  depends_on = [aws_api_gateway_integration.step_functions_integration]
}

resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.ai_assistant_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.generate.id,
      aws_api_gateway_method.post_generate.id,
      aws_api_gateway_integration.step_functions_integration.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_api_gateway_integration.step_functions_integration]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.ai_assistant_api.id
  stage_name    = "prod"
}

output "api_invoke_url" {
  value = "${aws_api_gateway_stage.prod.invoke_url}/generate"
}
