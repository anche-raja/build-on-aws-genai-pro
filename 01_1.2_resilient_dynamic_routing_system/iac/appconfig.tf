resource "aws_appconfig_application" "ai_assistant_app" {
  name        = "AIAssistantApp"
  description = "AI Assistant Application for Dynamic Routing"
}

resource "aws_appconfig_environment" "production" {
  name           = "Production"
  application_id = aws_appconfig_application.ai_assistant_app.id
}

resource "aws_appconfig_configuration_profile" "model_selection_strategy" {
  application_id = aws_appconfig_application.ai_assistant_app.id
  description    = "Model Selection Strategy Profile"
  name           = "ModelSelectionStrategy"
  location_uri   = "hosted"
  type           = "AWS.Freeform"
}

resource "aws_appconfig_hosted_configuration_version" "v1" {
  application_id           = aws_appconfig_application.ai_assistant_app.id
  configuration_profile_id = aws_appconfig_configuration_profile.model_selection_strategy.configuration_profile_id
  content_type             = "application/json"
  content                  = file("${path.module}/../model_selection_strategy.json")
}

resource "aws_appconfig_deployment" "initial_deployment" {
  application_id           = aws_appconfig_application.ai_assistant_app.id
  configuration_profile_id = aws_appconfig_configuration_profile.model_selection_strategy.configuration_profile_id
  configuration_version    = aws_appconfig_hosted_configuration_version.v1.version_number
  deployment_strategy_id   = "AppConfig.AllAtOnce"
  description              = "Initial deployment of model selection strategy"
  environment_id           = aws_appconfig_environment.production.environment_id
}

output "app_config_application_id" {
  value = aws_appconfig_application.ai_assistant_app.id
}

output "app_config_environment_id" {
  value = aws_appconfig_environment.production.environment_id
}

output "app_config_configuration_profile_id" {
  value = aws_appconfig_configuration_profile.model_selection_strategy.configuration_profile_id
}

