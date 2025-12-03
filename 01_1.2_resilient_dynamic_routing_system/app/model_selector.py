import boto3
import json
import os

def lambda_handler(event, context):

    appconfig_client = boto3.client('appconfig')
    
    # These names must match the resources created
    app_name = os.environ.get('APPCONFIG_APPLICATION', 'AIAssistantApp')
    env_name = os.environ.get('APPCONFIG_ENVIRONMENT', 'Production')
    config_profile = os.environ.get('APPCONFIG_PROFILE', 'ModelSelectionStrategy')
    
    try:
        config_response = appconfig_client.get_configuration(
            Application=app_name,
            Environment=env_name,
            Configuration=config_profile,
            ClientId='AIAssistantLambda'
        )
        
        # Parse configuration
        config = json.loads(config_response['Content'].read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching configuration: {e}")
        # Fallback config if AppConfig fails
        config = {"primary_model": "anthropic.claude-3-sonnet-20240229-v1:0"}
    
    # Extract request details
    # When invoked via Step Functions (Express), the payload is passed directly as the event
    # When invoked via API Gateway Proxy, the payload is in 'body'
    if 'body' in event:
        try:
            body = json.loads(event.get('body', '{}'))
        except (TypeError, json.JSONDecodeError):
             # Handle case where body might already be a dict (if pre-parsed)
            body = event.get('body', {}) if isinstance(event.get('body'), dict) else {}
    else:
        # Assume direct invocation payload
        body = event

    prompt = body.get('prompt', '')
    use_case = body.get('use_case', 'general')
    
    # Select model based on use case and configuration
    model_id = select_model(config, use_case)
    
    # Invoke selected model
    response = invoke_model(model_id, prompt)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'model_used': model_id,
            'response': response
        })
    }

def select_model(config, use_case):
    """Select appropriate model based on configuration and use case."""
    # Check if there's a use case specific model
    use_case_models = config.get('use_case_models', {})
    if use_case in use_case_models:
        return use_case_models[use_case]
    
    # Default to primary model
    return config.get('primary_model')

def invoke_model(model_id, prompt):
    """Invoke the selected model with error handling."""
    bedrock_runtime = boto3.client('bedrock-runtime')
    
    try:
        # Prepare request body based on model provider
        if "anthropic" in model_id:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })
        elif "amazon" in model_id:
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 500,
                    "temperature": 0.7,
                    "topP": 0.9
                }
            })
        else:
            # Basic fallback or error for unknown models
            return f"Error: Unsupported model provider for {model_id}"

        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode())
        
        if "anthropic" in model_id:
            return response_body['content'][0]['text']
        elif "amazon" in model_id:
            return response_body['results'][0]['outputText']
        
    except Exception as e:
        print(f"Error invoking model {model_id}: {str(e)}")
        # RAISE the exception so Step Functions catches it as States.TaskFailed
        raise e

