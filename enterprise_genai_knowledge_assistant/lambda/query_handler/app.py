"""
Query Handler Lambda Function
Handles user queries and generates AI-powered responses
"""

import json
import boto3
import os
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

# Environment variables
METADATA_TABLE = os.environ['METADATA_TABLE']
CONVERSATION_TABLE = os.environ['CONVERSATION_TABLE']
EVALUATION_TABLE = os.environ['EVALUATION_TABLE']
OPENSEARCH_DOMAIN = os.environ['OPENSEARCH_DOMAIN']
AWS_REGION = os.environ['AWS_REGION']


def handler(event, context):
    """
    Lambda handler for query processing
    
    Args:
        event: API Gateway event containing user query
        context: Lambda context
        
    Returns:
        dict: API Gateway response with AI-generated answer
    """
    try:
        # Parse request body
        body = json.loads(event['body'])
        query = body['query']
        conversation_id = body.get('conversation_id', f"conv-{int(datetime.now().timestamp())}")
        max_results = body.get('max_results', 5)
        
        print(f"Processing query: {query}")
        
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # Search for relevant documents
        search_results = search_documents(query_embedding, max_results)
        
        # Extract context from results
        context = extract_context(search_results)
        
        # Generate AI response
        answer = generate_response(query, context)
        
        # Store conversation history
        store_conversation(conversation_id, query, answer)
        
        # Prepare sources for response
        sources = format_sources(search_results)
        
        return create_response(200, {
            'answer': answer,
            'sources': sources,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })


def generate_embedding(text):
    """Generate text embedding using Amazon Bedrock"""
    response = bedrock_runtime.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        body=json.dumps({"inputText": text})
    )
    
    result = json.loads(response['body'].read())
    return result['embedding']


def search_documents(query_embedding, max_results):
    """Search OpenSearch for relevant documents using vector similarity"""
    client = get_opensearch_client()
    
    results = client.search(
        index='documents',
        body={
            'size': max_results,
            'query': {
                'knn': {
                    'embedding': {
                        'vector': query_embedding,
                        'k': max_results
                    }
                }
            }
        }
    )
    
    return results['hits']['hits']


def extract_context(search_results):
    """Extract and combine content from search results"""
    context_parts = []
    
    for hit in search_results:
        content = hit['_source']['content']
        context_parts.append(content)
    
    return "\n\n".join(context_parts)


def generate_response(query, context):
    """Generate AI response using Amazon Bedrock"""
    prompt = f"""Based on the following context, answer the question accurately and concisely.

Context:
{context}

Question: {query}

Answer:"""
    
    response = bedrock_runtime.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{
                "role": "user",
                "content": prompt
            }]
        })
    )
    
    result = json.loads(response['body'].read())
    return result['content'][0]['text']


def store_conversation(conversation_id, query, answer):
    """Store conversation in DynamoDB"""
    table = dynamodb.Table(CONVERSATION_TABLE)
    timestamp = int(datetime.now().timestamp())
    ttl = timestamp + (30 * 24 * 60 * 60)  # 30 days
    
    table.put_item(Item={
        'conversation_id': conversation_id,
        'timestamp': timestamp,
        'query': query,
        'response': answer,
        'ttl': ttl
    })


def format_sources(search_results):
    """Format search results as source references"""
    sources = []
    
    for hit in search_results:
        sources.append({
            'document_id': hit['_id'],
            'relevance_score': float(hit['_score']),
            'excerpt': hit['_source']['content'][:200] + '...'
        })
    
    return sources


def get_opensearch_client():
    """Create OpenSearch client with AWS authentication"""
    credentials = boto3.Session().get_credentials()
    
    auth = AWSRequestsAuth(
        aws_access_key=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_token=credentials.token,
        aws_host=OPENSEARCH_DOMAIN,
        aws_region=AWS_REGION,
        aws_service='es'
    )
    
    return OpenSearch(
        hosts=[{'host': OPENSEARCH_DOMAIN, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )


def create_response(status_code, body):
    """Create API Gateway response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS,POST,PUT,DELETE',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }

