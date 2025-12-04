"""
Lambda Function: Sync Scheduler
Triggered by EventBridge to check for stale documents and trigger updates
"""

import json
import os
import boto3
from datetime import datetime, timedelta

from app.sync_manager import SyncManager
from app.metadata_manager import MetadataManager


# Environment variables
REGION = os.environ.get('AWS_REGION', 'us-east-1')
METADATA_TABLE = os.environ.get('METADATA_TABLE_NAME', 'DocumentMetadata')
BUCKET_NAME = os.environ.get('BUCKET_NAME', '')
MAX_AGE_DAYS = int(os.environ.get('MAX_AGE_DAYS', '30'))
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', '')

# Initialize managers
sync_manager = SyncManager(region=REGION)
metadata_manager = MetadataManager(table_name=METADATA_TABLE, region=REGION)
sfn_client = boto3.client('stepfunctions', region_name=REGION)


def lambda_handler(event, context):
    """
    Check for stale documents and trigger sync workflows
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Response with sync status
    """
    print(f"Starting sync check at {datetime.utcnow().isoformat()}")
    
    try:
        # Get overall sync status
        sync_status = sync_manager.get_sync_status(METADATA_TABLE)
        print(f"Current sync status: {json.dumps(sync_status, indent=2)}")
        
        # Find stale documents
        stale_docs = sync_manager.get_stale_documents(
            metadata_table_name=METADATA_TABLE,
            max_age_days=MAX_AGE_DAYS
        )
        
        print(f"Found {len(stale_docs)} stale documents")
        
        # Find modified objects in S3
        since_date = datetime.utcnow() - timedelta(days=1)  # Check last 24 hours
        modified_objects = sync_manager.list_modified_objects(
            bucket=BUCKET_NAME,
            prefix='documents/',
            since=since_date
        )
        
        print(f"Found {len(modified_objects)} modified objects in S3")
        
        # Create update batches
        documents_to_update = []
        
        # Add stale documents
        for doc in stale_docs[:100]:  # Limit to 100 per run
            documents_to_update.append({
                'document_id': doc['document_id'],
                'source_key': doc.get('source_key', ''),
                'reason': 'stale'
            })
        
        # Add modified documents
        for obj in modified_objects[:50]:  # Limit to 50 per run
            documents_to_update.append({
                'source_key': obj['key'],
                'reason': 'modified'
            })
        
        # Create batches
        batches = sync_manager.create_update_batch(documents_to_update, batch_size=10)
        
        print(f"Created {len(batches)} update batches")
        
        # Trigger Step Functions workflow for each batch
        executions = []
        for i, batch in enumerate(batches[:10]):  # Process max 10 batches per run
            execution_name = f"sync-batch-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{i}"
            
            if STATE_MACHINE_ARN:
                response = sfn_client.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=execution_name,
                    input=json.dumps({
                        'batch': batch,
                        'batch_index': i,
                        'total_batches': len(batches)
                    })
                )
                
                executions.append({
                    'execution_arn': response['executionArn'],
                    'batch_size': len(batch)
                })
        
        print(f"Started {len(executions)} Step Functions executions")
        
        # Cleanup deleted sources
        if BUCKET_NAME:
            cleanup_result = sync_manager.cleanup_deleted_sources(
                metadata_table_name=METADATA_TABLE,
                bucket=BUCKET_NAME,
                prefix='documents/'
            )
            print(f"Cleanup result: {json.dumps(cleanup_result)}")
        else:
            cleanup_result = {'status': 'skipped'}
        
        # Prepare response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'sync_status': sync_status,
                'stale_documents': len(stale_docs),
                'modified_objects': len(modified_objects),
                'batches_created': len(batches),
                'executions_started': len(executions),
                'cleanup': cleanup_result,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
        return response
        
    except Exception as e:
        print(f"Error in sync scheduler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


if __name__ == "__main__":
    # Test locally
    result = lambda_handler({}, None)
    print(json.dumps(result, indent=2))

