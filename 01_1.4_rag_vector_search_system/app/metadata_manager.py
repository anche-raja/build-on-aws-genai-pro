"""
Phase 1: DynamoDB Metadata Manager
Handles document metadata storage and retrieval
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataManager:
    """Manages document metadata in DynamoDB"""
    
    def __init__(self, table_name: str = 'DocumentMetadata', region: str = 'us-east-1'):
        """
        Initialize metadata manager
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table_name = table_name
        self.table = None
    
    def create_table(self) -> Dict:
        """
        Create the DynamoDB table for document metadata
        
        Returns:
            Table creation response
        """
        try:
            self.table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'document_id',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'chunk_id',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'document_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'chunk_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'document_type',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'last_updated',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'source',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'DocumentTypeIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'document_type',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'last_updated',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    },
                    {
                        'IndexName': 'SourceIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'source',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'last_updated',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                ],
                BillingMode='PAY_PER_REQUEST',
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'RAG-Vector-Search'
                    }
                ]
            )
            
            # Wait for table to be created
            self.table.wait_until_exists()
            logger.info(f"Created DynamoDB table: {self.table_name}")
            return {'status': 'success', 'table_name': self.table_name}
            
        except Exception as e:
            logger.error(f"Error creating table: {str(e)}")
            raise
    
    def get_table(self):
        """Get reference to existing table"""
        if not self.table:
            self.table = self.dynamodb.Table(self.table_name)
        return self.table
    
    def store_document_metadata(self, metadata: Dict) -> Dict:
        """
        Store metadata for a document chunk
        
        Args:
            metadata: Dictionary containing document metadata
                Required fields: document_id, chunk_id
                
        Returns:
            Response from DynamoDB
        """
        table = self.get_table()
        
        # Add timestamp if not present
        if 'last_updated' not in metadata:
            metadata['last_updated'] = datetime.utcnow().isoformat()
        
        try:
            response = table.put_item(Item=metadata)
            logger.info(f"Stored metadata for {metadata['document_id']}/{metadata['chunk_id']}")
            return response
        except Exception as e:
            logger.error(f"Error storing metadata: {str(e)}")
            raise
    
    def batch_store_metadata(self, metadata_list: List[Dict]) -> Dict:
        """
        Batch store multiple metadata entries
        
        Args:
            metadata_list: List of metadata dictionaries
            
        Returns:
            Summary of batch operation
        """
        table = self.get_table()
        
        try:
            with table.batch_writer() as batch:
                for metadata in metadata_list:
                    if 'last_updated' not in metadata:
                        metadata['last_updated'] = datetime.utcnow().isoformat()
                    batch.put_item(Item=metadata)
            
            logger.info(f"Batch stored {len(metadata_list)} metadata entries")
            return {'status': 'success', 'count': len(metadata_list)}
            
        except Exception as e:
            logger.error(f"Error batch storing metadata: {str(e)}")
            raise
    
    def get_document_metadata(self, document_id: str, chunk_id: Optional[str] = None) -> Dict:
        """
        Retrieve metadata for a document or specific chunk
        
        Args:
            document_id: Document ID
            chunk_id: Optional chunk ID (if None, returns all chunks)
            
        Returns:
            Metadata dictionary or list of metadata
        """
        table = self.get_table()
        
        try:
            if chunk_id:
                response = table.get_item(
                    Key={
                        'document_id': document_id,
                        'chunk_id': chunk_id
                    }
                )
                return response.get('Item', {})
            else:
                response = table.query(
                    KeyConditionExpression=Key('document_id').eq(document_id)
                )
                return response.get('Items', [])
                
        except Exception as e:
            logger.error(f"Error retrieving metadata: {str(e)}")
            raise
    
    def query_by_document_type(
        self,
        document_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Query documents by type and optional date range
        
        Args:
            document_type: Type of document
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
            
        Returns:
            List of matching metadata entries
        """
        table = self.get_table()
        
        try:
            key_condition = Key('document_type').eq(document_type)
            
            if start_date and end_date:
                key_condition = key_condition & Key('last_updated').between(start_date, end_date)
            elif start_date:
                key_condition = key_condition & Key('last_updated').gte(start_date)
            elif end_date:
                key_condition = key_condition & Key('last_updated').lte(end_date)
            
            response = table.query(
                IndexName='DocumentTypeIndex',
                KeyConditionExpression=key_condition
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Error querying by document type: {str(e)}")
            raise
    
    def query_by_source(self, source: str) -> List[Dict]:
        """
        Query documents by source
        
        Args:
            source: Source identifier (e.g., 'wiki', 'web', 'dms')
            
        Returns:
            List of matching metadata entries
        """
        table = self.get_table()
        
        try:
            response = table.query(
                IndexName='SourceIndex',
                KeyConditionExpression=Key('source').eq(source)
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Error querying by source: {str(e)}")
            raise
    
    def update_metadata(
        self,
        document_id: str,
        chunk_id: str,
        updates: Dict
    ) -> Dict:
        """
        Update specific fields in metadata
        
        Args:
            document_id: Document ID
            chunk_id: Chunk ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated metadata
        """
        table = self.get_table()
        
        # Build update expression
        update_expr = "SET "
        expr_attr_values = {}
        expr_attr_names = {}
        
        for i, (key, value) in enumerate(updates.items()):
            attr_name = f"#attr{i}"
            attr_value = f":val{i}"
            
            if i > 0:
                update_expr += ", "
            update_expr += f"{attr_name} = {attr_value}"
            
            expr_attr_names[attr_name] = key
            expr_attr_values[attr_value] = value
        
        # Add last_updated timestamp
        update_expr += ", #last_updated = :last_updated"
        expr_attr_names['#last_updated'] = 'last_updated'
        expr_attr_values[':last_updated'] = datetime.utcnow().isoformat()
        
        try:
            response = table.update_item(
                Key={
                    'document_id': document_id,
                    'chunk_id': chunk_id
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values,
                ReturnValues='ALL_NEW'
            )
            
            logger.info(f"Updated metadata for {document_id}/{chunk_id}")
            return response.get('Attributes', {})
            
        except Exception as e:
            logger.error(f"Error updating metadata: {str(e)}")
            raise
    
    def delete_document_metadata(self, document_id: str) -> Dict:
        """
        Delete all metadata for a document
        
        Args:
            document_id: Document ID
            
        Returns:
            Summary of deletion
        """
        table = self.get_table()
        
        try:
            # First, query all chunks for this document
            response = table.query(
                KeyConditionExpression=Key('document_id').eq(document_id)
            )
            
            items = response.get('Items', [])
            
            # Delete each chunk
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            'document_id': item['document_id'],
                            'chunk_id': item['chunk_id']
                        }
                    )
            
            logger.info(f"Deleted metadata for document {document_id} ({len(items)} chunks)")
            return {'status': 'success', 'deleted_count': len(items)}
            
        except Exception as e:
            logger.error(f"Error deleting metadata: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    manager = MetadataManager()
    
    # Example metadata
    metadata = {
        'document_id': 'doc-123',
        'chunk_id': 'doc-123-0',
        'title': 'Sample Document',
        'document_type': 'technical',
        'source': 'wiki',
        'author': 'John Doe',
        'chunk_index': 0,
        'chunk_text': 'Sample text content',
        'embedding_status': 'completed'
    }
    
    print("Metadata Manager initialized")




