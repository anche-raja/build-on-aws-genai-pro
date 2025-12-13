"""
Lambda Function: Capture User Query

Captures and validates user queries, initializes sessions, and prepares
data for the Step Functions workflow.
"""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any

# Import app modules (deployed as Lambda layer or in package)
try:
    from app.conversation_handler import ConversationHandler
    from app.guardrails_manager import GuardrailsManager
except ImportError:
    # Fallback for local testing
    import sys
    sys.path.append(os.path.dirname(__file__))
    from app.conversation_handler import ConversationHandler
    from app.guardrails_manager import GuardrailsManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONVERSATION_TABLE = os.environ.get('CONVERSATION_TABLE', 'customer-support-conversations')
REGION = os.environ.get('AWS_REGION', 'us-east-1')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for capturing user queries.
    
    Args:
        event: Lambda event containing user query
        context: Lambda context
        
    Returns:
        Response with session info and validated query
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract query from event
        query = event.get('query', '')
        session_id = event.get('session_id')
        user_id = event.get('user_id', 'anonymous')
        metadata = event.get('metadata', {})
        
        # Validate query
        if not query or not query.strip():
            return {
                'statusCode': 400,
                'error': 'Query is required',
                'query': query
            }
        
        # Create or retrieve session
        conversation_handler = ConversationHandler(
            dynamodb_table=CONVERSATION_TABLE,
            region=REGION
        )
        
        if not session_id:
            # Create new session
            session_id = str(uuid.uuid4())
            session = conversation_handler.create_session(
                session_id=session_id,
                metadata={
                    'user_id': user_id,
                    'source': metadata.get('source', 'api'),
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Created new session: {session_id}")
        else:
            # Retrieve existing session
            session = conversation_handler.get_session(session_id)
            if not session:
                return {
                    'statusCode': 404,
                    'error': 'Session not found',
                    'session_id': session_id
                }
        
        # Validate input with guardrails
        guardrails_manager = GuardrailsManager(region=REGION)
        input_safe, input_issues = guardrails_manager.validate_input(query)
        
        if not input_safe:
            # Return safe response for guardrail violations
            safe_response = guardrails_manager._generate_safe_response(
                input_issues, []
            )
            
            logger.warning(f"Guardrail triggered: {input_issues}")
            
            return {
                'statusCode': 200,
                'session_id': session_id,
                'query': query,
                'guardrail_triggered': True,
                'response': safe_response,
                'skip_processing': True
            }
        
        # Add user message to conversation history
        conversation_handler.add_message(
            session_id=session_id,
            role='user',
            content=query,
            metadata={'timestamp': datetime.utcnow().isoformat()}
        )
        
        # Prepare response
        response = {
            'statusCode': 200,
            'session_id': session_id,
            'query': query,
            'user_id': user_id,
            'turn_count': session.get('turn_count', 0) + 1,
            'guardrail_triggered': False,
            'skip_processing': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Query captured successfully for session {session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error capturing query: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e),
            'query': event.get('query', '')
        }


# For local testing
if __name__ == "__main__":
    test_event = {
        'query': 'My EC2 instance is not responding to SSH connections',
        'user_id': 'test-user-123'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))



