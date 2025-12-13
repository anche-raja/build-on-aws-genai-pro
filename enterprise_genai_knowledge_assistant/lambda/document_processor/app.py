"""
Document Processor Lambda Function
Enhanced with dynamic chunking and token counting
"""

import json
import os
import boto3
import uuid
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

try:
    import tiktoken
except ImportError:
    # Fallback if tiktoken is not available
    tiktoken = None

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')

# Environment variables
METADATA_TABLE = os.environ['METADATA_TABLE']
OPENSEARCH_DOMAIN = os.environ['OPENSEARCH_DOMAIN']
DOCUMENT_BUCKET = os.environ['DOCUMENT_BUCKET']
OPENSEARCH_SECRET = os.environ.get('OPENSEARCH_SECRET')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize tokenizer for token counting
tokenizer = tiktoken.get_encoding("cl100k_base") if tiktoken else None


def handler(event, context):
    """
    Enhanced Lambda handler with support for S3-based document processing
    """
    try:
        # Parse request body
        body = json.loads(event['body'])
        
        # Support both inline content and S3-based processing
        if 'document_key' in body:
            # S3-based processing
            document_key = body['document_key']
            document_type = body.get('document_type', 'text')
            
            # Get document from S3
            document_content = get_document_from_s3(DOCUMENT_BUCKET, document_key)
            
            if not document_content:
                return create_response(404, {'error': 'Document not found'})
            
            # Process document based on type
            if document_type == 'pdf':
                chunks = process_pdf_document(document_content)
            else:
                chunks = process_text_document(document_content)
            
            document_id = str(uuid.uuid4())
            metadata = {
                'document_key': document_key,
                'document_type': document_type
            }
        else:
            # Inline content processing (backward compatible)
            document_id = body.get('document_id', str(uuid.uuid4()))
            content = body['content']
            metadata = body.get('metadata', {})
            
            # Process as single chunk or multiple chunks
            chunks = process_text_document(content)
        
        # Generate embeddings for each chunk
        chunk_embeddings = []
        for chunk in chunks:
            embedding = generate_embedding(chunk['text'])
            chunk['embedding'] = embedding
            chunk_embeddings.append(chunk)
        
        # Store document metadata in DynamoDB
        store_metadata(document_id, metadata, chunks)
        
        # Index chunks in OpenSearch
        index_chunks_in_opensearch(document_id, chunk_embeddings)
        
        return create_response(200, {
            'status': 'success',
            'document_id': document_id,
            'chunk_count': len(chunks),
            'total_tokens': sum(chunk.get('tokens', 0) for chunk in chunks),
            'message': 'Document processed successfully'
        })
    
    except KeyError as e:
        print(f"Missing required field: {str(e)}")
        return create_response(400, {
            'status': 'error',
            'message': f'Missing required field: {str(e)}'
        })
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        })


def get_document_from_s3(bucket, key):
    """Get document content from S3"""
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error getting document from S3: {str(e)}")
        return None


def process_text_document(text):
    """
    Process text document with dynamic chunking based on semantic structure
    """
    chunks = []
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    current_chunk = ""
    current_chunk_tokens = 0
    max_chunk_tokens = 1000  # Target chunk size
    
    for paragraph in paragraphs:
        if tokenizer:
            paragraph_tokens = len(tokenizer.encode(paragraph))
        else:
            # Fallback: estimate ~4 chars per token
            paragraph_tokens = len(paragraph) // 4
        
        # If adding this paragraph would exceed target chunk size
        # and we already have content, save current chunk and start new one
        if current_chunk_tokens + paragraph_tokens > max_chunk_tokens and current_chunk:
            chunk_id = str(uuid.uuid4())
            chunks.append({
                'id': chunk_id,
                'text': current_chunk.strip(),
                'tokens': current_chunk_tokens
            })
            current_chunk = paragraph
            current_chunk_tokens = paragraph_tokens
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += paragraph
            current_chunk_tokens += paragraph_tokens
    
    # Don't forget the last chunk
    if current_chunk:
        chunk_id = str(uuid.uuid4())
        chunks.append({
            'id': chunk_id,
            'text': current_chunk.strip(),
            'tokens': current_chunk_tokens
        })
    
    return chunks if chunks else [{
        'id': str(uuid.uuid4()),
        'text': text,
        'tokens': len(tokenizer.encode(text)) if tokenizer else len(text) // 4
    }]


def process_pdf_document(content):
    """
    Process PDF document
    Note: In production, use proper PDF parsing library
    """
    # For now, treat as text
    return process_text_document(content)


def generate_embedding(text):
    """Generate text embedding using Amazon Bedrock"""
    try:
        response = bedrock_runtime.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text})
        )
        
        response_body = json.loads(response['body'].read())
        embedding = response_body['embedding']
        
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        # Return a zero vector as fallback
        return [0.0] * 1536


def store_metadata(document_id, metadata, chunks):
    """Store document metadata in DynamoDB"""
    try:
        table = dynamodb.Table(METADATA_TABLE)
        
        item = {
            'id': document_id,
            'metadata': metadata,
            'chunk_count': len(chunks),
            'processed_date': datetime.utcnow().isoformat(),
            'total_tokens': sum(chunk.get('tokens', 0) for chunk in chunks),
            'processed': True
        }
        
        table.put_item(Item=item)
    except Exception as e:
        print(f"Error storing metadata: {str(e)}")
        raise


def index_chunks_in_opensearch(document_id, chunks):
    """Index document chunks in OpenSearch with KNN vectors"""
    try:
        client = get_opensearch_client()
        index_name = "document-chunks"
        
        # Create index if it doesn't exist (idempotent)
        try:
            if not client.indices.exists(index=index_name):
                index_mapping = {
                    "mappings": {
                        "properties": {
                            "document_id": {"type": "keyword"},
                            "chunk_id": {"type": "keyword"},
                            "text": {"type": "text"},
                            "tokens": {"type": "integer"},
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": 1536
                            }
                        }
                    },
                    "settings": {
                        "index": {
                            "knn": True,
                            "knn.space_type": "cosinesimil"
                        }
                    }
                }
                client.indices.create(index=index_name, body=index_mapping)
        except Exception as e:
            print(f"Index might already exist: {str(e)}")
        
        # Index each chunk
        for chunk in chunks:
            doc_body = {
                "document_id": document_id,
                "chunk_id": chunk['id'],
                "text": chunk['text'],
                "tokens": chunk.get('tokens', 0),
                "embedding": chunk['embedding']
            }
            
            client.index(
                index=index_name,
                id=f"{document_id}_{chunk['id']}",
                body=doc_body
            )
        
        print(f"Indexed {len(chunks)} chunks for document {document_id}")
        return True
    except Exception as e:
        print(f"Error indexing chunks in OpenSearch: {str(e)}")
        raise


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