resource "aws_route53_health_check" "primary_region_health_check" {
  fqdn              = "${aws_api_gateway_rest_api.ai_assistant_api.id}.execute-api.us-east-1.amazonaws.com"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/prod/generate"
  failure_threshold = "3"
  request_interval  = "30"

  tags = {
    Name = "primary-region-health-check"
  }
}

# Assuming you have an existing hosted zone or creating a new one
# If using an existing zone, use data source:
# data "aws_route53_zone" "main" {
#   name = "yourdomain.com."
# }

# For this example, we'll assume creating a new zone or you can uncomment the data source above
resource "aws_route53_zone" "main" {
  name = "ai-assistant-demo.com" # Replace with your domain
}

resource "aws_route53_record" "primary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "ai-assistant.ai-assistant-demo.com"
  type    = "A"

  failover_routing_policy {
    type = "PRIMARY"
  }

  set_identifier  = "Primary"
  health_check_id = aws_route53_health_check.primary_region_health_check.id

  alias {
    name                   = "${aws_api_gateway_rest_api.ai_assistant_api.id}.execute-api.us-east-1.amazonaws.com"
    zone_id                = "Z1UJRXOUMOOFQ8" # API Gateway hosted zone ID for us-east-1 (Static)
    evaluate_target_health = true
  }
}

# For the secondary record, you would typically have deployed the stack to a second region (e.g., us-west-2)
# Since we are currently only deploying to one region in this Terraform config, 
# we can placeholder the secondary record or point it to a static failover page/bucket.
#
# In a real multi-region setup, you'd use a separate provider for the secondary region and 
# reference the API Gateway ID from that region's deployment.

resource "aws_route53_record" "secondary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "ai-assistant.ai-assistant-demo.com"
  type    = "A"

  failover_routing_policy {
    type = "SECONDARY"
  }

  set_identifier = "Secondary"

  # Placeholder for secondary region API Gateway
  # In a real scenario, this would be the API Gateway DNS from the secondary region
  alias {
    name                   = "example-api-id.execute-api.us-west-2.amazonaws.com" 
    zone_id                = "Z2OJLYMUO9EFXC" # API Gateway hosted zone ID for us-west-2 (Static)
    evaluate_target_health = true
  }
}

