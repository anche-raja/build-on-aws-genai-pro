"""
Lambda Function: RAG API Handler
API Gateway handler for RAG queries
"""

import json
import os
from typing import Dict, Any

from app.rag_application import RAGApplication
from app.bedrock_manager import BedrockManager
from app.opensearch_manager import OpenSearchManager
from app.metadata_manager import MetadataManager


# Environment variables
REGION = os.environ.get('AWS_REGION', 'us-east-1')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT', '')
INDEX_NAME = os.environ.get('INDEX_NAME', 'documents')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

# Initialize components
bedrock = BedrockManager(region_name=REGION)

opensearch = None
if OPENSEARCH_ENDPOINT:
    opensearch = OpenSearchManager(domain_endpoint=OPENSEARCH_ENDPOINT, region=REGION)

rag_app = RAGApplication(
    bedrock_manager=bedrock,
    opensearch_manager=opensearch
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle RAG API requests
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    print(f"Received request: {json.dumps(event)}")
    
    try:
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # Extract parameters
        query = body.get('query', '')
        conversation_history = body.get('conversation_history', [])
        filters = body.get('filters')
        num_results = body.get('num_results', 5)
        
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Query parameter is required'
                })
            }
        
        # Determine data source
        knowledge_base_id = KNOWLEDGE_BASE_ID if KNOWLEDGE_BASE_ID else None
        index_name = INDEX_NAME if OPENSEARCH_ENDPOINT else None
        
        # Generate response
        if conversation_history:
            response = rag_app.conversation_response(
                query=query,
                conversation_history=conversation_history,
                knowledge_base_id=knowledge_base_id,
                index_name=index_name,
                model_id=MODEL_ID
            )
        else:
            response = rag_app.generate_response(
                query=query,
                knowledge_base_id=knowledge_base_id,
                index_name=index_name,
                model_id=MODEL_ID,
                num_context_chunks=num_results,
                filters=filters
            )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response)
        }
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }


def handle_feedback(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle feedback submission
    
    Args:
        event: API Gateway event with feedback data
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        query = body.get('query', '')
        response_data = body.get('response', {})
        rating = body.get('rating', 0)
        comment = body.get('comment')
        
        if not query or not rating:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Query and rating are required'})
            }
        
        feedback = rag_app.collect_feedback(
            query=query,
            response=response_data,
            rating=rating,
            comment=comment
        )
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Feedback received',
                'feedback_id': feedback.get('timestamp', '')
            })
        }
        
    except Exception as e:
        print(f"Error handling feedback: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }


if __name__ == "__main__":
    # Test locally
    test_event = {
        'body': json.dumps({
            'query': 'What is Amazon Bedrock?',
            'num_results': 3
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))





