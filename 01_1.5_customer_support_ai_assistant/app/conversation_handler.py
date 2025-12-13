"""
Conversation Handler

Manages conversation flow, context, and history for multi-turn interactions.
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationHandler:
    """Handles conversation state and multi-turn interactions."""
    
    def __init__(
        self,
        dynamodb_table: str,
        region: str = "us-east-1",
        ttl_hours: int = 24
    ):
        """
        Initialize the Conversation Handler.
        
        Args:
            dynamodb_table: DynamoDB table for conversation history
            region: AWS region
            ttl_hours: Time-to-live for conversation sessions in hours
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(dynamodb_table)
        self.ttl_hours = ttl_hours
    
    def create_session(self, session_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a new conversation session.
        
        Args:
            session_id: Unique session identifier
            metadata: Optional session metadata
            
        Returns:
            Session information
        """
        try:
            timestamp = datetime.utcnow()
            ttl_timestamp = timestamp + timedelta(hours=self.ttl_hours)
            
            session = {
                'session_id': session_id,
                'created_at': timestamp.isoformat(),
                'updated_at': timestamp.isoformat(),
                'ttl': int(ttl_timestamp.timestamp()),
                'turn_count': 0,
                'messages': [],
                'metadata': metadata or {},
                'status': 'active'
            }
            
            self.table.put_item(Item=self._convert_to_dynamodb(session))
            
            logger.info(f"Created session: {session_id}")
            return session
            
        except ClientError as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        try:
            response = self.table.get_item(Key={'session_id': session_id})
            
            if 'Item' in response:
                return self._convert_from_dynamodb(response['Item'])
            
            return None
            
        except ClientError as e:
            logger.error(f"Error retrieving session: {e}")
            return None
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            Success boolean
        """
        try:
            timestamp = datetime.utcnow()
            
            message = {
                'role': role,
                'content': content,
                'timestamp': timestamp.isoformat(),
                'metadata': metadata or {}
            }
            
            # Update session with new message
            response = self.table.update_item(
                Key={'session_id': session_id},
                UpdateExpression=(
                    "SET messages = list_append(if_not_exists(messages, :empty_list), :message), "
                    "updated_at = :updated_at, "
                    "turn_count = turn_count + :inc"
                ),
                ExpressionAttributeValues={
                    ':message': [self._convert_to_dynamodb(message)],
                    ':empty_list': [],
                    ':updated_at': timestamp.isoformat(),
                    ':inc': 1
                },
                ReturnValues="UPDATED_NEW"
            )
            
            logger.info(f"Added message to session {session_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    def get_conversation_history(
        self,
        session_id: str,
        max_turns: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            max_turns: Maximum number of turns to retrieve
            
        Returns:
            List of messages
        """
        session = self.get_session(session_id)
        
        if not session:
            return []
        
        messages = session.get('messages', [])
        
        # Return last N turns (each turn is user + assistant message)
        return messages[-(max_turns * 2):] if messages else []
    
    def format_history_for_prompt(
        self,
        session_id: str,
        max_turns: int = 5
    ) -> str:
        """
        Format conversation history for inclusion in prompts.
        
        Args:
            session_id: Session identifier
            max_turns: Maximum number of turns to include
            
        Returns:
            Formatted history string
        """
        messages = self.get_conversation_history(session_id, max_turns)
        
        if not messages:
            return "No previous conversation."
        
        formatted = []
        for msg in messages:
            role = msg['role'].upper()
            content = msg['content']
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update session metadata.
        
        Args:
            session_id: Session identifier
            metadata: Metadata to update
            
        Returns:
            Success boolean
        """
        try:
            self.table.update_item(
                Key={'session_id': session_id},
                UpdateExpression="SET metadata = :metadata, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ':metadata': self._convert_to_dynamodb(metadata),
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except ClientError as e:
            logger.error(f"Error updating metadata: {e}")
            return False
    
    def end_session(self, session_id: str) -> bool:
        """
        Mark a session as ended.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Success boolean
        """
        try:
            self.table.update_item(
                Key={'session_id': session_id},
                UpdateExpression="SET #status = :status, ended_at = :ended_at",
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'ended',
                    ':ended_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Ended session: {session_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error ending session: {e}")
            return False
    
    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a summary of the conversation context.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Context summary
        """
        session = self.get_session(session_id)
        
        if not session:
            return {'error': 'Session not found'}
        
        messages = session.get('messages', [])
        
        # Extract key information
        user_queries = [m['content'] for m in messages if m['role'] == 'user']
        detected_services = set()
        
        # Simple service detection
        aws_services = ['ec2', 's3', 'lambda', 'rds', 'dynamodb', 'cloudformation',
                       'cloudwatch', 'iam', 'vpc', 'elb', 'route53', 'cloudfront']
        
        for query in user_queries:
            query_lower = query.lower()
            for service in aws_services:
                if service in query_lower:
                    detected_services.add(service.upper())
        
        return {
            'session_id': session_id,
            'turn_count': session.get('turn_count', 0),
            'duration_minutes': self._calculate_duration(session),
            'detected_services': list(detected_services),
            'user_queries_count': len(user_queries),
            'status': session.get('status', 'unknown')
        }
    
    def _calculate_duration(self, session: Dict[str, Any]) -> float:
        """Calculate session duration in minutes."""
        try:
            created = datetime.fromisoformat(session['created_at'])
            updated = datetime.fromisoformat(session['updated_at'])
            duration = (updated - created).total_seconds() / 60
            return round(duration, 2)
        except:
            return 0.0
    
    def _convert_to_dynamodb(self, obj: Any) -> Any:
        """Convert Python objects to DynamoDB compatible format."""
        if isinstance(obj, dict):
            return {k: self._convert_to_dynamodb(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_dynamodb(item) for item in obj]
        elif isinstance(obj, float):
            return Decimal(str(obj))
        else:
            return obj
    
    def _convert_from_dynamodb(self, obj: Any) -> Any:
        """Convert DynamoDB objects to Python format."""
        if isinstance(obj, dict):
            return {k: self._convert_from_dynamodb(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_from_dynamodb(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        else:
            return obj



