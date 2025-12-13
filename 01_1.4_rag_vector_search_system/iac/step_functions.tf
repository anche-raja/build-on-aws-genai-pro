# Step Functions State Machine for Sync Workflow
resource "aws_sfn_state_machine" "sync_workflow" {
  name     = "${var.project_name}-sync-workflow"
  role_arn = aws_iam_role.step_functions.arn
  
  definition = jsonencode({
    Comment = "Sync workflow for document updates"
    StartAt = "ProcessBatch"
    States = {
      ProcessBatch = {
        Type = "Map"
        ItemsPath = "$.batch"
        MaxConcurrency = 5
        Iterator = {
          StartAt = "ProcessDocument"
          States = {
            ProcessDocument = {
              Type = "Task"
              Resource = aws_lambda_function.document_processor.arn
              Retry = [
                {
                  ErrorEquals = ["States.TaskFailed"]
                  IntervalSeconds = 2
                  MaxAttempts = 3
                  BackoffRate = 2.0
                }
              ]
              Catch = [
                {
                  ErrorEquals = ["States.ALL"]
                  Next = "HandleError"
                }
              ]
              End = true
            }
            HandleError = {
              Type = "Pass"
              Result = "Error handled"
              End = true
            }
          }
        }
        Next = "CompleteBatch"
      }
      CompleteBatch = {
        Type = "Pass"
        Result = "Batch processing complete"
        End = true
      }
    }
  })
  
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  
  tags = {
    Name = "${var.project_name}-sync-workflow"
  }
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/vendedlogs/states/${var.project_name}-sync-workflow"
  retention_in_days = 14
  
  tags = {
    Name = "${var.project_name}-sfn-logs"
  }
}




