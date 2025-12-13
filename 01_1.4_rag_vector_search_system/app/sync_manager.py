"""
Phase 5: Data Maintenance and Synchronization
Handles change detection, incremental updates, and data freshness
"""

import boto3
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyncManager:
    """Manages data synchronization and updates"""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize sync manager
        
        Args:
            region: AWS region
        """
        self.s3 = boto3.client('s3', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.region = region
    
    def detect_changes(
        self,
        bucket: str,
        key: str,
        stored_checksum: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if a document has changed
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            stored_checksum: Previously stored checksum
            
        Returns:
            Tuple of (has_changed, new_checksum)
        """
        try:
            # Get object
            response = self.s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            # Calculate new checksum
            new_checksum = hashlib.md5(content).hexdigest()
            
            # Compare checksums
            has_changed = new_checksum != stored_checksum
            
            if has_changed:
                logger.info(f"Change detected in {key}")
            
            return has_changed, new_checksum
            
        except Exception as e:
            logger.error(f"Error detecting changes for {key}: {str(e)}")
            raise
    
    def get_stale_documents(
        self,
        metadata_table_name: str,
        max_age_days: int = 30
    ) -> List[Dict]:
        """
        Find documents that haven't been updated recently
        
        Args:
            metadata_table_name: DynamoDB table name
            max_age_days: Maximum age in days before considered stale
            
        Returns:
            List of stale documents
        """
        table = self.dynamodb.Table(metadata_table_name)
        cutoff_date = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
        
        try:
            # Scan for old documents (in production, use a GSI)
            response = table.scan(
                FilterExpression='last_updated < :cutoff',
                ExpressionAttributeValues={
                    ':cutoff': cutoff_date
                }
            )
            
            stale_docs = response.get('Items', [])
            logger.info(f"Found {len(stale_docs)} stale documents")
            
            return stale_docs
            
        except Exception as e:
            logger.error(f"Error finding stale documents: {str(e)}")
            raise
    
    def list_modified_objects(
        self,
        bucket: str,
        prefix: str = '',
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        List S3 objects modified since a given time
        
        Args:
            bucket: S3 bucket name
            prefix: Optional prefix to filter objects
            since: Optional datetime to filter modified objects
            
        Returns:
            List of modified objects
        """
        modified_objects = []
        paginator = self.s3.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    if since is None or obj['LastModified'] > since:
                        modified_objects.append({
                            'key': obj['Key'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'size': obj['Size'],
                            'etag': obj['ETag']
                        })
            
            logger.info(f"Found {len(modified_objects)} modified objects")
            return modified_objects
            
        except Exception as e:
            logger.error(f"Error listing modified objects: {str(e)}")
            raise
    
    def create_update_batch(
        self,
        documents: List[Dict],
        batch_size: int = 10
    ) -> List[List[Dict]]:
        """
        Create batches of documents for processing
        
        Args:
            documents: List of documents to process
            batch_size: Number of documents per batch
            
        Returns:
            List of document batches
        """
        batches = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} batches for {len(documents)} documents")
        return batches
    
    def mark_for_reindexing(
        self,
        metadata_table_name: str,
        document_id: str,
        reason: str = 'manual_trigger'
    ) -> Dict:
        """
        Mark a document for reindexing
        
        Args:
            metadata_table_name: DynamoDB table name
            document_id: Document ID to mark
            reason: Reason for reindexing
            
        Returns:
            Update response
        """
        table = self.dynamodb.Table(metadata_table_name)
        
        try:
            # Query all chunks for this document
            response = table.query(
                KeyConditionExpression='document_id = :doc_id',
                ExpressionAttributeValues={
                    ':doc_id': document_id
                }
            )
            
            # Update each chunk
            for item in response.get('Items', []):
                table.update_item(
                    Key={
                        'document_id': document_id,
                        'chunk_id': item['chunk_id']
                    },
                    UpdateExpression='SET reindex_required = :true, reindex_reason = :reason, marked_at = :timestamp',
                    ExpressionAttributeValues={
                        ':true': True,
                        ':reason': reason,
                        ':timestamp': datetime.utcnow().isoformat()
                    }
                )
            
            logger.info(f"Marked document {document_id} for reindexing")
            return {'status': 'success', 'document_id': document_id}
            
        except Exception as e:
            logger.error(f"Error marking document for reindexing: {str(e)}")
            raise
    
    def get_sync_status(self, metadata_table_name: str) -> Dict:
        """
        Get overall synchronization status
        
        Args:
            metadata_table_name: DynamoDB table name
            
        Returns:
            Status summary
        """
        table = self.dynamodb.Table(metadata_table_name)
        
        try:
            # Scan table for status (in production, use aggregation)
            response = table.scan(
                ProjectionExpression='document_id, embedding_status, last_updated'
            )
            
            items = response.get('Items', [])
            
            # Calculate statistics
            total_docs = len(set(item['document_id'] for item in items))
            total_chunks = len(items)
            completed = sum(1 for item in items if item.get('embedding_status') == 'completed')
            pending = sum(1 for item in items if item.get('embedding_status') == 'pending')
            failed = sum(1 for item in items if item.get('embedding_status') == 'failed')
            
            # Find oldest and newest updates
            if items:
                last_updates = [item.get('last_updated', '') for item in items if item.get('last_updated')]
                oldest_update = min(last_updates) if last_updates else None
                newest_update = max(last_updates) if last_updates else None
            else:
                oldest_update = None
                newest_update = None
            
            status = {
                'total_documents': total_docs,
                'total_chunks': total_chunks,
                'completed_chunks': completed,
                'pending_chunks': pending,
                'failed_chunks': failed,
                'completion_rate': round(completed / total_chunks * 100, 2) if total_chunks > 0 else 0,
                'oldest_update': oldest_update,
                'newest_update': newest_update,
                'checked_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Sync status: {status['completion_rate']}% complete")
            return status
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            raise
    
    def cleanup_deleted_sources(
        self,
        metadata_table_name: str,
        bucket: str,
        prefix: str = ''
    ) -> Dict:
        """
        Remove metadata for documents no longer in S3
        
        Args:
            metadata_table_name: DynamoDB table name
            bucket: S3 bucket name
            prefix: Optional prefix
            
        Returns:
            Cleanup summary
        """
        table = self.dynamodb.Table(metadata_table_name)
        
        try:
            # Get all documents from DynamoDB
            response = table.scan(
                ProjectionExpression='document_id, source_key'
            )
            db_documents = response.get('Items', [])
            
            # Get all objects from S3
            s3_keys = set()
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    s3_keys.add(obj['Key'])
            
            # Find documents to delete
            to_delete = []
            for doc in db_documents:
                if doc.get('source_key') not in s3_keys:
                    to_delete.append(doc['document_id'])
            
            # Delete metadata
            deleted_count = 0
            for doc_id in to_delete:
                # Query all chunks
                chunks_response = table.query(
                    KeyConditionExpression='document_id = :doc_id',
                    ExpressionAttributeValues={':doc_id': doc_id}
                )
                
                # Delete each chunk
                with table.batch_writer() as batch:
                    for item in chunks_response.get('Items', []):
                        batch.delete_item(
                            Key={
                                'document_id': item['document_id'],
                                'chunk_id': item['chunk_id']
                            }
                        )
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} chunks from {len(to_delete)} deleted documents")
            return {
                'status': 'success',
                'deleted_documents': len(to_delete),
                'deleted_chunks': deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up deleted sources: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    manager = SyncManager()
    
    # Example: Check sync status
    # status = manager.get_sync_status('DocumentMetadata')
    # print(json.dumps(status, indent=2))
    
    print("Sync Manager initialized")




