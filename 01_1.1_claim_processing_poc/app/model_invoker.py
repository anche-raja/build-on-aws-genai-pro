import boto3
import json
import os
from typing import List, Dict, Any, Optional

class ModelInvoker:
    def __init__(self, region_name: str = "us-east-1"):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region_name)

    def invoke_messages(self, 
                       messages: List[Dict[str, Any]], 
                       model_id: str = "amazon.nova-micro-v1:0",
                       max_tokens: int = 1000,
                       temperature: float = 0.0,
                       top_p: float = 0.9) -> Optional[str]:
        """
        Invokes a Bedrock model using the Messages API format (standard for Nova, Claude 3, etc.).
        
        Args:
            messages: List of message objects (e.g. [{"role": "user", "content": [{"text": "..."}]}])
            model_id: The ID of the model to invoke
            max_tokens: Maximum tokens to generate
            temperature: Randomness (0.0 = deterministic)
            top_p: Nucleus sampling parameter
            
        Returns:
            The text content of the response, or None if error.
        """
        try:
            body = {
                "messages": messages,
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens,
                    "topP": top_p
                }
            }
            
            # Handle Anthropic-specific fields if needed (Claude models differ slightly in params)
            if "anthropic" in model_id:
                # Map generic config to Anthropic specific top-level fields if using older models
                # But for consistency, assuming we use the Converse API or standard Messages API 
                # If using raw invoke with Claude, structure is slightly different. 
                # For this PoC with Amazon Nova, the above structure is correct.
                pass

            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Amazon Nova / Generic Messages API response path
            if 'output' in response_body:
                return response_body['output']['message']['content'][0]['text']
            # Fallback for other potential formats
            elif 'content' in response_body:
                 return response_body['content'][0]['text']
                 
            return str(response_body)

        except Exception as e:
            print(f"Error invoking model {model_id}: {str(e)}")
            raise e

    def invoke_text(self, prompt_text: str, **kwargs) -> str:
        """
        Helper wrapper to create a simple user message from text.
        """
        messages = [
            {
                "role": "user", 
                "content": [{"text": prompt_text}]
            }
        ]
        return self.invoke_messages(messages, **kwargs)

