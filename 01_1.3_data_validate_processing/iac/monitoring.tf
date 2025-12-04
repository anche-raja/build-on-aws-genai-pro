locals {
  dashboard_name = "CustomerFeedbackQuality"
}

resource "aws_cloudwatch_dashboard" "customer_feedback_quality" {
  dashboard_name = local.dashboard_name

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CustomerFeedback/TextQuality", "QualityScore", "Source", "TextReviews"]
          ]
          period = 86400
          stat   = "Average"
          region = "us-east-1"
          title  = "Text Review Quality Score"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CustomerFeedback/DataQuality", "RulesetPassRate", "Ruleset", "customer_reviews_ruleset"]
          ]
          period = 86400
          stat   = "Average"
          region = "us-east-1"
          title  = "Glue Data Quality Pass Rate"
        }
      }
    ]
  })
}

