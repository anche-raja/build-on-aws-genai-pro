# EventBridge Rule for Scheduled Sync
resource "aws_cloudwatch_event_rule" "sync_schedule" {
  name                = "${var.project_name}-sync-schedule"
  description         = "Trigger sync scheduler on schedule"
  schedule_expression = var.sync_schedule_expression
  
  tags = {
    Name = "${var.project_name}-sync-schedule"
  }
}

resource "aws_cloudwatch_event_target" "sync_scheduler" {
  rule      = aws_cloudwatch_event_rule.sync_schedule.name
  target_id = "SyncSchedulerTarget"
  arn       = aws_lambda_function.sync_scheduler.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sync_scheduler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sync_schedule.arn
}

