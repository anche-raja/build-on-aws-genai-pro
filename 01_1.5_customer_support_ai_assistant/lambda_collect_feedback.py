"""
Lambda Function: Collect Feedback

Collects user feedback and implicit behavioral signals.
"""

import json
import os
import logging
from typing import Dict, Any

try:
    from app.feedback_collector import FeedbackCollector
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from app.feedback_collector import FeedbackCollector

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
FEEDBACK_TABLE = os.environ.get('FEEDBACK_TABLE', 'customer-support-feedback')
REGION = os.environ.get('AWS_REGION', 'us-east-1')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for collecting feedback.
    
    Args:
        event: Lambda event with feedback data
        context: Lambda context
        
    Returns:
        Response with feedback collection status
    """
    try:
        logger.info("Collecting feedback")
        
        # Extract data from event
        session_id = event.get('session_id')
        interaction_id = event.get('interaction_id', session_id)
        feedback_type = event.get('feedback_type', 'implicit')
        rating = event.get('rating')
        comments = event.get('comments')
        
        # Extract metadata for context
        metadata = {
            'intent': event.get('intent'),
            'template_id': event.get('template_id'),
            'quality_score': event.get('quality_score'),
            'response_type': event.get('response_type'),
            'model_id': event.get('model_id')
        }
        
        # Initialize feedback collector
        feedback_collector = FeedbackCollector(
            dynamodb_table=FEEDBACK_TABLE,
            region=REGION
        )
        
        # Collect explicit feedback if provided
        if feedback_type in ['thumbs_up', 'thumbs_down', 'rating', 'comment']:
            success = feedback_collector.collect_feedback(
                session_id=session_id,
                interaction_id=interaction_id,
                feedback_type=feedback_type,
                rating=rating,
                comments=comments,
                metadata=metadata
            )
            
            logger.info(f"Explicit feedback collected: {feedback_type}")
        
        # Collect implicit feedback
        implicit_metrics = {
            'quality_passed': event.get('quality_passed', True),
            'needs_regeneration': event.get('needs_regeneration', False),
            'needs_clarification': event.get('needs_clarification', False),
            'escalation_required': event.get('escalation_required', False),
            'guardrail_triggered': event.get('guardrail_triggered', False),
            'intent_confidence': event.get('intent_confidence', 0.5)
        }
        
        feedback_collector.collect_implicit_feedback(
            session_id=session_id,
            interaction_id=interaction_id,
            metrics=implicit_metrics
        )
        
        logger.info("Implicit feedback collected")
        
        # Return event with feedback status
        return {
            **event,
            'feedback_collected': True
        }
        
    except Exception as e:
        logger.error(f"Error collecting feedback: {str(e)}", exc_info=True)
        return {
            **event,
            'feedback_collected': False,
            'feedback_error': str(e)
        }


def analyze_feedback_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Separate handler for analyzing feedback (can be triggered by schedule).
    
    Args:
        event: Lambda event with analysis parameters
        context: Lambda context
        
    Returns:
        Analysis results
    """
    try:
        logger.info("Analyzing feedback")
        
        # Extract parameters
        time_range_hours = event.get('time_range_hours', 24)
        template_id = event.get('template_id')
        intent = event.get('intent')
        
        # Initialize feedback collector
        feedback_collector = FeedbackCollector(
            dynamodb_table=FEEDBACK_TABLE,
            region=REGION
        )
        
        # Analyze feedback
        analysis = feedback_collector.analyze_feedback(
            time_range_hours=time_range_hours,
            template_id=template_id,
            intent=intent
        )
        
        logger.info(f"Analyzed {analysis.get('total_feedback', 0)} feedback items")
        logger.info(f"Satisfaction rate: {analysis.get('statistics', {}).get('satisfaction_rate', 0)}%")
        
        # Log recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            logger.info(f"Recommendations: {recommendations}")
        
        return {
            'statusCode': 200,
            'analysis': analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing feedback: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e)
        }


# For local testing
if __name__ == "__main__":
    # Test feedback collection
    test_event = {
        'session_id': 'test-session-123',
        'interaction_id': 'interaction-456',
        'feedback_type': 'thumbs_up',
        'intent': 'ec2_troubleshooting',
        'template_id': 'ec2_troubleshooting',
        'quality_score': 85.0,
        'quality_passed': True
    }
    
    result = lambda_handler(test_event, None)
    print("Feedback Collection:")
    print(json.dumps(result, indent=2))
    
    # Test feedback analysis
    analysis_event = {
        'time_range_hours': 24
    }
    
    analysis_result = analyze_feedback_handler(analysis_event, None)
    print("\nFeedback Analysis:")
    print(json.dumps(analysis_result, indent=2, default=str))



