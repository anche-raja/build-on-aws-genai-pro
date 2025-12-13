"""
Feedback Handler
Phase 6: User feedback collection endpoint
"""

import json
import os

def handle_feedback(event, context, quality_evaluator):
    """
    Handle user feedback submission
    
    Expected body:
    {
        "request_id": "abc-123",
        "user_id": "user@example.com",
        "feedback_type": "thumbs_up|thumbs_down|rating|comment",
        "rating": 1-5 (optional),
        "comment": "text" (optional)
    }
    """
    try:
        body = json.loads(event['body'])
        
        request_id = body.get('request_id')
        user_id = body.get('user_id', 'anonymous')
        feedback_type = body.get('feedback_type')
        rating = body.get('rating')
        comment = body.get('comment')
        
        # Validate required fields
        if not request_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing request_id'})
            }
        
        if not feedback_type:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing feedback_type'})
            }
        
        # Validate feedback_type
        valid_types = ['thumbs_up', 'thumbs_down', 'rating', 'comment']
        if feedback_type not in valid_types:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'Invalid feedback_type. Must be one of: {", ".join(valid_types)}'
                })
            }
        
        # Validate rating if provided
        if rating is not None:
            try:
                rating = int(rating)
                if not 1 <= rating <= 5:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({'error': 'Rating must be between 1 and 5'})
                    }
            except (ValueError, TypeError):
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': 'Rating must be a number'})
                }
        
        # Collect feedback
        if quality_evaluator:
            feedback_id = quality_evaluator.collect_user_feedback(
                request_id=request_id,
                user_id=user_id,
                feedback_type=feedback_type,
                rating=rating,
                comment=comment
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Feedback received successfully',
                    'feedback_id': feedback_id
                })
            }
        else:
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Quality evaluator not available'})
            }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    
    except Exception as e:
        print(f"Error handling feedback: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

