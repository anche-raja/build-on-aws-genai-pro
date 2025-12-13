"""
Lambda Function: Detect Intent

Detects user intent using Amazon Comprehend and custom classification logic.
"""

import json
import os
import logging
from typing import Dict, Any

try:
    from app.intent_detector import IntentDetector
    from app.conversation_handler import ConversationHandler
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from app.intent_detector import IntentDetector
    from app.conversation_handler import ConversationHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONVERSATION_TABLE = os.environ.get('CONVERSATION_TABLE', 'customer-support-conversations')
REGION = os.environ.get('AWS_REGION', 'us-east-1')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for intent detection.
    
    Args:
        event: Lambda event containing query and session info
        context: Lambda context
        
    Returns:
        Response with detected intent and confidence
    """
    try:
        logger.info(f"Detecting intent for event: {json.dumps(event)}")
        
        # Check if processing should be skipped (guardrail triggered)
        if event.get('skip_processing'):
            logger.info("Skipping intent detection due to guardrail")
            return event
        
        # Extract data from event
        query = event.get('query', '')
        session_id = event.get('session_id')
        
        if not query:
            return {
                **event,
                'error': 'Query is required for intent detection'
            }
        
        # Get conversation history for context
        conversation_history = []
        if session_id:
            conversation_handler = ConversationHandler(
                dynamodb_table=CONVERSATION_TABLE,
                region=REGION
            )
            conversation_history = conversation_handler.get_conversation_history(
                session_id=session_id,
                max_turns=3
            )
        
        # Detect intent
        intent_detector = IntentDetector(region=REGION)
        intent_result = intent_detector.detect_intent(
            query=query,
            conversation_history=conversation_history
        )
        
        # Log detection results
        logger.info(
            f"Intent detected: {intent_result['intent']} "
            f"(confidence: {intent_result['confidence']:.2f})"
        )
        
        # Add intent information to event
        response = {
            **event,
            'intent': intent_result['intent'],
            'intent_confidence': intent_result['confidence'],
            'is_confident': intent_result['is_confident'],
            'needs_clarification': intent_result['needs_clarification'],
            'template_id': intent_result['template_id'],
            'escalation_required': intent_result.get('escalation_required', False),
            'detected_services': intent_result.get('detected_services', []),
            'sentiment': intent_result.get('sentiment', {}),
            'alternative_intents': intent_result.get('alternative_intents', [])
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error detecting intent: {str(e)}", exc_info=True)
        return {
            **event,
            'error': f"Intent detection error: {str(e)}",
            'intent': 'general_support',
            'intent_confidence': 0.5,
            'is_confident': False,
            'needs_clarification': True,
            'template_id': 'general_support'
        }


# For local testing
if __name__ == "__main__":
    test_event = {
        'query': 'My EC2 instance is not responding to SSH connections',
        'session_id': 'test-session-123',
        'user_id': 'test-user'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))


