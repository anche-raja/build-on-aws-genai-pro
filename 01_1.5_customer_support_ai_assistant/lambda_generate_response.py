"""
Lambda Function: Generate Response

Generates AI response using Amazon Bedrock with appropriate prompt template.
"""

import json
import os
import logging
from typing import Dict, Any

try:
    from app.bedrock_prompt_manager import BedrockPromptManager
    from app.conversation_handler import ConversationHandler
    from app.guardrails_manager import GuardrailsManager
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from app.bedrock_prompt_manager import BedrockPromptManager
    from app.conversation_handler import ConversationHandler
    from app.guardrails_manager import GuardrailsManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONVERSATION_TABLE = os.environ.get('CONVERSATION_TABLE', 'customer-support-conversations')
PROMPT_TABLE = os.environ.get('PROMPT_TABLE', 'customer-support-prompts')
S3_BUCKET = os.environ.get('PROMPT_BUCKET')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for generating AI responses.
    
    Args:
        event: Lambda event with query, intent, and context
        context: Lambda context
        
    Returns:
        Response with AI-generated content
    """
    try:
        logger.info(f"Generating response for event")
        
        # Check if processing should be skipped
        if event.get('skip_processing'):
            logger.info("Skipping response generation")
            return event
        
        # Check if clarification is needed
        if event.get('needs_clarification'):
            logger.info("Clarification needed, generating clarification question")
            return generate_clarification_response(event)
        
        # Check if escalation is required
        if event.get('escalation_required'):
            logger.info("Escalation required")
            return generate_escalation_response(event)
        
        # Extract data from event
        query = event.get('query', '')
        session_id = event.get('session_id')
        template_id = event.get('template_id', 'general_support')
        
        # Initialize managers
        prompt_manager = BedrockPromptManager(
            region=REGION,
            s3_bucket=S3_BUCKET,
            dynamodb_table=PROMPT_TABLE
        )
        
        conversation_handler = ConversationHandler(
            dynamodb_table=CONVERSATION_TABLE,
            region=REGION
        )
        
        # Get conversation history
        history = conversation_handler.format_history_for_prompt(
            session_id=session_id,
            max_turns=5
        )
        
        # Get prompt template
        template = prompt_manager.get_prompt_template(template_id)
        
        # Format prompt with parameters
        formatted_prompt = prompt_manager.format_prompt(
            template=template,
            parameters={
                'query': query,
                'history': history
            }
        )
        
        logger.info(f"Using template: {template_id}")
        
        # Invoke model
        model_response = prompt_manager.invoke_model(
            prompt=formatted_prompt,
            model_id=MODEL_ID,
            max_tokens=2048,
            temperature=0.7
        )
        
        if not model_response.get('success'):
            raise Exception(f"Model invocation failed: {model_response.get('error')}")
        
        response_content = model_response['content']
        
        # Validate output with guardrails
        guardrails_manager = GuardrailsManager(region=REGION)
        output_safe, output_issues = guardrails_manager.validate_output(response_content)
        
        if not output_safe:
            logger.warning(f"Output guardrail triggered: {output_issues}")
            response_content = guardrails_manager._generate_safe_response([], output_issues)
        
        # Save assistant response to conversation history
        conversation_handler.add_message(
            session_id=session_id,
            role='assistant',
            content=response_content,
            metadata={
                'template_id': template_id,
                'model_id': MODEL_ID,
                'intent': event.get('intent'),
                'output_safe': output_safe
            }
        )
        
        # Prepare response
        response = {
            **event,
            'response': response_content,
            'model_id': MODEL_ID,
            'template_id': template_id,
            'output_guardrail_triggered': not output_safe,
            'usage': model_response.get('usage', {})
        }
        
        logger.info("Response generated successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
        return {
            **event,
            'error': f"Response generation error: {str(e)}",
            'response': "I apologize, but I encountered an error while processing your request. Please try again or contact AWS Support for assistance."
        }


def generate_clarification_response(event: Dict[str, Any]) -> Dict[str, Any]:
    """Generate clarification question when intent is unclear."""
    try:
        from app.intent_detector import IntentDetector
        
        intent_detector = IntentDetector(region=REGION)
        clarification_question = intent_detector.generate_clarification_question(event)
        
        # Save to conversation history
        session_id = event.get('session_id')
        if session_id:
            conversation_handler = ConversationHandler(
                dynamodb_table=CONVERSATION_TABLE,
                region=REGION
            )
            conversation_handler.add_message(
                session_id=session_id,
                role='assistant',
                content=clarification_question,
                metadata={'type': 'clarification'}
            )
        
        return {
            **event,
            'response': clarification_question,
            'response_type': 'clarification'
        }
        
    except Exception as e:
        logger.error(f"Error generating clarification: {str(e)}")
        return {
            **event,
            'response': "Could you please provide more details about your question or issue?",
            'response_type': 'clarification'
        }


def generate_escalation_response(event: Dict[str, Any]) -> Dict[str, Any]:
    """Generate escalation message for human handoff."""
    escalation_message = (
        "Thank you for contacting AWS Support. Based on your inquiry, "
        "I'd like to connect you with a specialist who can provide "
        "more detailed assistance. \n\n"
        "Your case has been escalated to our support team. "
        "You can expect a response from a support engineer soon. "
        "In the meantime, you can check the status of your case in the "
        "AWS Support Center."
    )
    
    # Save to conversation history
    session_id = event.get('session_id')
    if session_id:
        try:
            conversation_handler = ConversationHandler(
                dynamodb_table=CONVERSATION_TABLE,
                region=REGION
            )
            conversation_handler.add_message(
                session_id=session_id,
                role='assistant',
                content=escalation_message,
                metadata={'type': 'escalation'}
            )
            conversation_handler.update_session_metadata(
                session_id=session_id,
                metadata={'escalated': True}
            )
        except Exception as e:
            logger.error(f"Error saving escalation message: {str(e)}")
    
    return {
        **event,
        'response': escalation_message,
        'response_type': 'escalation'
    }


# For local testing
if __name__ == "__main__":
    test_event = {
        'query': 'My EC2 instance is not responding',
        'session_id': 'test-session-123',
        'intent': 'ec2_troubleshooting',
        'template_id': 'ec2_troubleshooting',
        'needs_clarification': False,
        'escalation_required': False
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2, default=str))



