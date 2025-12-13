"""
Lambda Function: Validate Quality

Validates the quality of AI-generated responses.
"""

import json
import os
import logging
from typing import Dict, Any

try:
    from app.quality_validator import QualityValidator
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from app.quality_validator import QualityValidator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
QUALITY_THRESHOLD = float(os.environ.get('QUALITY_THRESHOLD', '70.0'))
REGION = os.environ.get('AWS_REGION', 'us-east-1')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for quality validation.
    
    Args:
        event: Lambda event with query and response
        context: Lambda context
        
    Returns:
        Response with quality validation results
    """
    try:
        logger.info("Validating response quality")
        
        # Check if processing should be skipped
        if event.get('skip_processing'):
            logger.info("Skipping quality validation")
            return event
        
        # Extract data from event
        response_content = event.get('response', '')
        query = event.get('query', '')
        intent = event.get('intent')
        
        if not response_content:
            return {
                **event,
                'quality_validation': {
                    'is_valid': False,
                    'score': 0,
                    'error': 'No response to validate'
                }
            }
        
        # Validate quality
        quality_validator = QualityValidator()
        validation_result = quality_validator.validate_response(
            response=response_content,
            query=query,
            intent=intent
        )
        
        # Log validation results
        logger.info(
            f"Quality validation score: {validation_result['score']:.2f} "
            f"(threshold: {QUALITY_THRESHOLD})"
        )
        
        if not validation_result['is_valid']:
            logger.warning(f"Quality issues: {validation_result['issues']}")
        
        # Generate improvement suggestions if quality is low
        suggestions = []
        if validation_result['score'] < QUALITY_THRESHOLD:
            suggestions = quality_validator.generate_improvement_suggestions(
                validation_result
            )
        
        # Determine if regeneration is needed
        needs_regeneration = (
            validation_result['score'] < QUALITY_THRESHOLD and
            len(validation_result['issues']) > 0
        )
        
        # Add validation results to event
        result = {
            **event,
            'quality_validation': validation_result,
            'quality_score': validation_result['score'],
            'quality_passed': validation_result['is_valid'],
            'needs_regeneration': needs_regeneration,
            'improvement_suggestions': suggestions
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating quality: {str(e)}", exc_info=True)
        return {
            **event,
            'quality_validation': {
                'is_valid': True,  # Fail open
                'score': 75.0,
                'error': str(e)
            },
            'quality_passed': True
        }


# For local testing
if __name__ == "__main__":
    test_event = {
        'query': 'My EC2 instance is not responding',
        'response': '''I understand you're experiencing issues with your EC2 instance not responding. Let me help you troubleshoot this.

Here are the steps to diagnose the issue:

1. Check Instance Status Checks:
   - Go to EC2 Console
   - Select your instance
   - Check the Status Checks tab for any failures

2. Verify Security Groups:
   - Ensure port 22 (SSH) or 3389 (RDP) is open
   - Check that your IP is allowed in the inbound rules

3. Review Network Configuration:
   - Verify the instance has a public IP (if accessing from internet)
   - Check route tables and internet gateway configuration

4. Check System Logs:
   - Review system logs in the EC2 console
   - Look for boot or networking errors

Next steps:
- Try these troubleshooting steps and let me know what you find
- If the issue persists, I can help you dive deeper into specific areas

Would you like me to explain any of these steps in more detail?''',
        'intent': 'ec2_troubleshooting'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))


