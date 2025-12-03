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

resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.ai_assistant_api.id
  resource_id             = aws_api_gateway_resource.generate.id
  http_method             = aws_api_gateway_method.post_generate.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ai_assistant_lambda.invoke_arn
}

resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.ai_assistant_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.generate.id,
      aws_api_gateway_method.post_generate.id,
      aws_api_gateway_integration.lambda_integration.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.ai_assistant_api.id
  stage_name    = "prod"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ai_assistant_lambda.function_name
  principal     = "apigateway.amazonaws.com"

  # The source ARN is specific to the API Gateway execution
  # Format: arn:aws:execute-api:region:account-id:api-id/stage/method/resource-path
  source_arn = "${aws_api_gateway_rest_api.ai_assistant_api.execution_arn}/prod/POST/generate"
}

output "api_invoke_url" {
  value = "${aws_api_gateway_stage.prod.invoke_url}/generate"
}

