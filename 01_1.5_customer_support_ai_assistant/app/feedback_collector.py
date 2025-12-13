"""
Feedback Collector

Collects and analyzes feedback to improve prompts and responses iteratively.
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from botocore.exceptions import ClientError
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects and analyzes user feedback."""
    
    def __init__(
        self,
        dynamodb_table: str,
        region: str = "us-east-1"
    ):
        """
        Initialize the Feedback Collector.
        
        Args:
            dynamodb_table: DynamoDB table for feedback storage
            region: AWS region
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(dynamodb_table)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
    
    def collect_feedback(
        self,
        session_id: str,
        interaction_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        comments: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Collect feedback for an interaction.
        
        Args:
            session_id: Session identifier
            interaction_id: Specific interaction identifier
            feedback_type: Type of feedback (thumbs_up, thumbs_down, rating, comment)
            rating: Optional numerical rating (1-5)
            comments: Optional text comments
            metadata: Optional metadata (intent, template_id, etc.)
            
        Returns:
            Success boolean
        """
        try:
            feedback = {
                'feedback_id': f"{session_id}#{interaction_id}",
                'session_id': session_id,
                'interaction_id': interaction_id,
                'feedback_type': feedback_type,
                'rating': rating,
                'comments': comments,
                'metadata': self._convert_to_dynamodb(metadata or {}),
                'timestamp': datetime.utcnow().isoformat(),
                'processed': False
            }
            
            self.table.put_item(Item=self._convert_to_dynamodb(feedback))
            
            # Send to CloudWatch
            self._send_to_cloudwatch(feedback)
            
            logger.info(f"Collected feedback for {interaction_id}: {feedback_type}")
            return True
            
        except ClientError as e:
            logger.error(f"Error collecting feedback: {e}")
            return False
    
    def collect_implicit_feedback(
        self,
        session_id: str,
        interaction_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Collect implicit feedback from user behavior.
        
        Args:
            session_id: Session identifier
            interaction_id: Interaction identifier
            metrics: Behavioral metrics (e.g., time_to_next_query, follow_up_needed)
            
        Returns:
            Success boolean
        """
        try:
            feedback = {
                'feedback_id': f"{session_id}#{interaction_id}#implicit",
                'session_id': session_id,
                'interaction_id': interaction_id,
                'feedback_type': 'implicit',
                'metrics': self._convert_to_dynamodb(metrics),
                'timestamp': datetime.utcnow().isoformat(),
                'processed': False
            }
            
            self.table.put_item(Item=self._convert_to_dynamodb(feedback))
            
            logger.info(f"Collected implicit feedback for {interaction_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error collecting implicit feedback: {e}")
            return False
    
    def analyze_feedback(
        self,
        time_range_hours: int = 24,
        template_id: Optional[str] = None,
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze collected feedback.
        
        Args:
            time_range_hours: Hours of feedback to analyze
            template_id: Optional filter by template
            intent: Optional filter by intent
            
        Returns:
            Analysis results
        """
        try:
            # Calculate time range
            cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
            
            # Scan feedback (in production, use GSI with timestamp)
            response = self.table.scan()
            items = response.get('Items', [])
            
            # Filter by time and criteria
            filtered_items = []
            for item in items:
                item_time = datetime.fromisoformat(item['timestamp'])
                if item_time >= cutoff_time:
                    metadata = item.get('metadata', {})
                    if template_id and metadata.get('template_id') != template_id:
                        continue
                    if intent and metadata.get('intent') != intent:
                        continue
                    filtered_items.append(self._convert_from_dynamodb(item))
            
            # Aggregate statistics
            stats = self._aggregate_statistics(filtered_items)
            
            # Identify issues and patterns
            issues = self._identify_issues(filtered_items)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(stats, issues)
            
            return {
                'time_range_hours': time_range_hours,
                'total_feedback': len(filtered_items),
                'statistics': stats,
                'issues': issues,
                'recommendations': recommendations,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            logger.error(f"Error analyzing feedback: {e}")
            return {'error': str(e)}
    
    def _aggregate_statistics(self, feedback_items: List[Dict]) -> Dict[str, Any]:
        """Aggregate feedback statistics."""
        stats = {
            'total_count': len(feedback_items),
            'by_type': defaultdict(int),
            'by_rating': defaultdict(int),
            'by_template': defaultdict(int),
            'by_intent': defaultdict(int),
            'average_rating': 0,
            'satisfaction_rate': 0
        }
        
        total_rating = 0
        rating_count = 0
        positive_count = 0
        
        for item in feedback_items:
            # Count by type
            feedback_type = item.get('feedback_type', 'unknown')
            stats['by_type'][feedback_type] += 1
            
            # Count by rating
            rating = item.get('rating')
            if rating:
                stats['by_rating'][rating] += 1
                total_rating += rating
                rating_count += 1
                if rating >= 4:
                    positive_count += 1
            
            # Count by type (thumbs up/down)
            if feedback_type == 'thumbs_up':
                positive_count += 1
            
            # Count by template
            metadata = item.get('metadata', {})
            template_id = metadata.get('template_id', 'unknown')
            stats['by_template'][template_id] += 1
            
            # Count by intent
            intent = metadata.get('intent', 'unknown')
            stats['by_intent'][intent] += 1
        
        # Calculate averages
        if rating_count > 0:
            stats['average_rating'] = round(total_rating / rating_count, 2)
        
        if len(feedback_items) > 0:
            stats['satisfaction_rate'] = round(positive_count / len(feedback_items) * 100, 2)
        
        # Convert defaultdicts to regular dicts
        stats['by_type'] = dict(stats['by_type'])
        stats['by_rating'] = dict(stats['by_rating'])
        stats['by_template'] = dict(stats['by_template'])
        stats['by_intent'] = dict(stats['by_intent'])
        
        return stats
    
    def _identify_issues(self, feedback_items: List[Dict]) -> List[Dict[str, Any]]:
        """Identify issues from feedback."""
        issues = []
        
        # Group by template
        template_feedback = defaultdict(list)
        for item in feedback_items:
            metadata = item.get('metadata', {})
            template_id = metadata.get('template_id', 'unknown')
            template_feedback[template_id].append(item)
        
        # Analyze each template
        for template_id, items in template_feedback.items():
            negative_count = sum(1 for item in items 
                               if item.get('feedback_type') == 'thumbs_down' 
                               or (item.get('rating') or 5) < 3)
            
            if len(items) >= 5 and negative_count / len(items) > 0.4:
                issues.append({
                    'type': 'low_satisfaction',
                    'template_id': template_id,
                    'severity': 'high',
                    'details': f"{negative_count}/{len(items)} negative feedback",
                    'sample_comments': [
                        item.get('comments') 
                        for item in items 
                        if item.get('comments')
                    ][:3]
                })
        
        # Identify common complaint themes
        all_comments = [item.get('comments', '') for item in feedback_items if item.get('comments')]
        if all_comments:
            common_themes = self._extract_complaint_themes(all_comments)
            for theme, count in common_themes.items():
                if count >= 3:
                    issues.append({
                        'type': 'common_complaint',
                        'theme': theme,
                        'severity': 'medium',
                        'count': count
                    })
        
        return issues
    
    def _extract_complaint_themes(self, comments: List[str]) -> Dict[str, int]:
        """Extract common themes from complaint comments."""
        themes = defaultdict(int)
        
        # Define theme keywords
        theme_keywords = {
            'too_technical': ['technical', 'jargon', 'complicated', 'complex'],
            'not_helpful': ['not helpful', 'useless', 'didnt help', "doesn't help"],
            'too_vague': ['vague', 'generic', 'not specific', 'unclear'],
            'wrong_service': ['wrong service', 'not what i asked', 'different service'],
            'missing_steps': ['missing steps', 'incomplete', 'need more detail']
        }
        
        for comment in comments:
            comment_lower = comment.lower()
            for theme, keywords in theme_keywords.items():
                if any(keyword in comment_lower for keyword in keywords):
                    themes[theme] += 1
        
        return dict(themes)
    
    def _generate_recommendations(
        self,
        stats: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Overall satisfaction
        satisfaction_rate = stats.get('satisfaction_rate', 0)
        if satisfaction_rate < 70:
            recommendations.append(
                f"Overall satisfaction rate is {satisfaction_rate}%. "
                "Consider reviewing and improving prompt templates."
            )
        elif satisfaction_rate >= 90:
            recommendations.append(
                f"Excellent satisfaction rate ({satisfaction_rate}%). "
                "Current approach is working well."
            )
        
        # Template-specific issues
        template_issues = [i for i in issues if i['type'] == 'low_satisfaction']
        if template_issues:
            for issue in template_issues:
                recommendations.append(
                    f"Template '{issue['template_id']}' has low satisfaction. "
                    f"Review and refine based on user feedback."
                )
        
        # Common complaints
        complaint_issues = [i for i in issues if i['type'] == 'common_complaint']
        if complaint_issues:
            for issue in complaint_issues:
                theme = issue['theme']
                if theme == 'too_technical':
                    recommendations.append(
                        "Multiple users find responses too technical. "
                        "Simplify language and add more explanations."
                    )
                elif theme == 'not_helpful':
                    recommendations.append(
                        "Users report responses not being helpful. "
                        "Focus on providing more actionable guidance."
                    )
                elif theme == 'too_vague':
                    recommendations.append(
                        "Responses are too vague. Include more specific "
                        "examples and step-by-step instructions."
                    )
        
        # Intent-specific recommendations
        intent_stats = stats.get('by_intent', {})
        for intent, count in intent_stats.items():
            if count >= 10:  # Significant volume
                intent_feedback = [
                    item for item in issues 
                    if item.get('template_id', '').startswith(intent)
                ]
                if intent_feedback:
                    recommendations.append(
                        f"Review prompt template for '{intent}' intent "
                        f"based on {count} interactions."
                    )
        
        return recommendations
    
    def _send_to_cloudwatch(self, feedback: Dict[str, Any]):
        """Send feedback metrics to CloudWatch."""
        try:
            metric_data = []
            
            # Feedback type metric
            metric_data.append({
                'MetricName': 'FeedbackCount',
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {'Name': 'FeedbackType', 'Value': feedback['feedback_type']}
                ]
            })
            
            # Rating metric
            if feedback.get('rating'):
                metric_data.append({
                    'MetricName': 'UserRating',
                    'Value': feedback['rating'],
                    'Unit': 'None',
                    'Timestamp': datetime.utcnow()
                })
            
            # Template performance
            metadata = feedback.get('metadata', {})
            if metadata.get('template_id'):
                metric_data.append({
                    'MetricName': 'TemplateUsage',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {'Name': 'TemplateId', 'Value': metadata['template_id']}
                    ]
                })
            
            self.cloudwatch.put_metric_data(
                Namespace='CustomerSupportAI',
                MetricData=metric_data
            )
            
        except ClientError as e:
            logger.warning(f"Error sending metrics to CloudWatch: {e}")
    
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


