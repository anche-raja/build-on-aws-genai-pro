"""
Lambda Function: Document Processing
Triggered by S3 object creation to process and embed documents
"""

import json
import os
import sys
import boto3
from datetime import datetime

# Import application modules
sys.path.append('/opt/python')  # Lambda layer path
from app.document_processor import DocumentProcessor
from app.bedrock_manager import BedrockManager
from app.metadata_manager import MetadataManager
from app.opensearch_manager import OpenSearchManager


# Initialize clients
REGION = os.environ.get('AWS_REGION', 'us-east-1')
METADATA_TABLE = os.environ.get('METADATA_TABLE_NAME', 'DocumentMetadata')
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT', '')
INDEX_NAME = os.environ.get('INDEX_NAME', 'documents')
CHUNKING_STRATEGY = os.environ.get('CHUNKING_STRATEGY', 'semantic')

processor = DocumentProcessor(region=REGION)
bedrock = BedrockManager(region_name=REGION)
metadata_manager = MetadataManager(table_name=METADATA_TABLE, region=REGION)

# Initialize OpenSearch if endpoint is provided
opensearch = None
if OPENSEARCH_ENDPOINT:
    opensearch = OpenSearchManager(domain_endpoint=OPENSEARCH_ENDPOINT, region=REGION)


def lambda_handler(event, context):
    """
    Process documents uploaded to S3
    
    Args:
        event: S3 event containing bucket and key information
        context: Lambda context
        
    Returns:
        Response with processing status
    """
    print(f"Received event: {json.dumps(event)}")
    
    processed_documents = []
    failed_documents = []
    
    for record in event['Records']:
        try:
            # Extract S3 information
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            print(f"Processing document: s3://{bucket}/{key}")
            
            # Process document
            result = processor.process_document_from_s3(
                bucket=bucket,
                key=key,
                chunking_strategy=CHUNKING_STRATEGY
            )
            
            document_id = result['document_id']
            chunks = result['chunks']
            metadata = result['metadata']
            
            # Store metadata and embeddings for each chunk
            documents_for_opensearch = []
            
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{document_id}-{i}"
                
                # Generate embedding
                print(f"Generating embedding for chunk {i+1}/{len(chunks)}")
                embedding = bedrock.generate_embedding(chunk_text)
                
                # Prepare metadata for DynamoDB
                chunk_metadata = {
                    'document_id': document_id,
                    'chunk_id': chunk_id,
                    'chunk_index': i,
                    'chunk_text': chunk_text,
                    'chunk_length': len(chunk_text),
                    'document_type': result['document_type'],
                    'source': 's3',
                    'source_bucket': bucket,
                    'source_key': key,
                    'checksum': result['checksum'],
                    'embedding_status': 'completed',
                    'last_updated': datetime.utcnow().isoformat(),
                    **metadata
                }
                
                # Store in DynamoDB
                metadata_manager.store_document_metadata(chunk_metadata)
                
                # Prepare for OpenSearch if available
                if opensearch:
                    opensearch_doc = {
                        'id': chunk_id,
                        'document_id': document_id,
                        'chunk_id': chunk_id,
                        'title': metadata.get('title', ''),
                        'content': chunk_text,
                        'embedding': embedding,
                        'metadata': {
                            'document_type': result['document_type'],
                            'source': 's3',
                            'created_at': metadata.get('created_at', ''),
                            'file_name': metadata.get('file_name', '')
                        }
                    }
                    documents_for_opensearch.append(opensearch_doc)
            
            # Bulk index to OpenSearch
            if opensearch and documents_for_opensearch:
                print(f"Indexing {len(documents_for_opensearch)} chunks to OpenSearch")
                opensearch.bulk_index_documents(INDEX_NAME, documents_for_opensearch)
            
            processed_documents.append({
                'document_id': document_id,
                'key': key,
                'chunks': len(chunks)
            })
            
            print(f"Successfully processed document {key}: {len(chunks)} chunks")
            
        except Exception as e:
            print(f"Error processing document {key}: {str(e)}")
            failed_documents.append({
                'key': key,
                'error': str(e)
            })
    
    # Return response
    response = {
        'statusCode': 200 if not failed_documents else 207,  # 207 = Multi-Status
        'body': json.dumps({
            'processed': len(processed_documents),
            'failed': len(failed_documents),
            'details': {
                'successful': processed_documents,
                'failed': failed_documents
            }
        })
    }
    
    return response


if __name__ == "__main__":
    # Test locally
    test_event = {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test-document.txt'}
                }
            }
        ]
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))





