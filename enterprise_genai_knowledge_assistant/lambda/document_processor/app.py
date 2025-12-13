"""
Document Processor Lambda Function
Handles document ingestion and embedding generation
"""

import json
import boto3
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')

# Environment variables
METADATA_TABLE = os.environ['METADATA_TABLE']
OPENSEARCH_DOMAIN = os.environ['OPENSEARCH_DOMAIN']
DOCUMENT_BUCKET = os.environ['DOCUMENT_BUCKET']
OPENSEARCH_SECRET = os.environ.get('OPENSEARCH_SECRET')
AWS_REGION = os.environ['AWS_REGION']


def handler(event, context):
    """
    Lambda handler for document processing
    
    Args:
        event: API Gateway event containing document data
        context: Lambda context
        
    Returns:
        dict: API Gateway response with processing status
    """
    try:
        # Parse request body
        body = json.loads(event['body'])
        document_id = body['document_id']
        content = body['content']
        metadata = body.get('metadata', {})
        
        print(f"Processing document: {document_id}")
        
        # Generate embeddings using Amazon Bedrock
        embedding = generate_embedding(content)
        
        # Store in OpenSearch for vector search
        store_in_opensearch(document_id, content, embedding, metadata)
        
        # Update metadata in DynamoDB
        update_metadata(document_id, metadata)
        
        return create_response(200, {
            'status': 'success',
            'document_id': document_id,
            'message': 'Document processed successfully'
        })
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
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


def store_in_opensearch(doc_id, content, embedding, metadata):
    """Store document and embedding in OpenSearch"""
    client = get_opensearch_client()
    
    client.index(
        index='documents',
        id=doc_id,
        body={
            'content': content,
            'embedding': embedding,
            'metadata': metadata
        }
    )


def update_metadata(doc_id, metadata):
    """Update document metadata in DynamoDB"""
    table = dynamodb.Table(METADATA_TABLE)
    
    table.put_item(Item={
        'id': doc_id,
        'metadata': metadata,
        'processed': True
    })


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

