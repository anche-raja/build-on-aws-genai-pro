"""
Intent Detector

Detects user intent and routes to appropriate prompt templates using
Amazon Comprehend and custom classification logic.
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentDetector:
    """Detects user intent from queries."""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the Intent Detector.
        
        Args:
            region: AWS region
        """
        self.comprehend = boto3.client('comprehend', region_name=region)
        
        # Define intent patterns
        self.intent_patterns = self._load_intent_patterns()
        
        # Define confidence thresholds
        self.confidence_threshold = 0.7
        self.clarification_threshold = 0.5
    
    def _load_intent_patterns(self) -> Dict[str, Dict]:
        """Load intent detection patterns."""
        return {
            'ec2_troubleshooting': {
                'keywords': [
                    'ec2', 'instance', 'virtual machine', 'vm', 'compute',
                    'instance not responding', 'cannot connect', 'ssh', 'rdp',
                    'instance status', 'instance stopped'
                ],
                'services': ['ec2', 'compute'],
                'description': 'EC2 instance troubleshooting and support',
                'template_id': 'ec2_troubleshooting'
            },
            's3_troubleshooting': {
                'keywords': [
                    's3', 'bucket', 'object storage', 'storage', 'file upload',
                    'access denied', '403', 'bucket policy', 'cors'
                ],
                'services': ['s3', 'storage'],
                'description': 'S3 storage troubleshooting and support',
                'template_id': 's3_troubleshooting'
            },
            'lambda_troubleshooting': {
                'keywords': [
                    'lambda', 'function', 'serverless', 'timeout', 'cold start',
                    'memory exceeded', 'execution error', 'lambda error'
                ],
                'services': ['lambda', 'serverless'],
                'description': 'Lambda function troubleshooting and support',
                'template_id': 'lambda_troubleshooting'
            },
            'rds_database': {
                'keywords': [
                    'rds', 'database', 'mysql', 'postgresql', 'aurora',
                    'db instance', 'connection string', 'database connection'
                ],
                'services': ['rds', 'database'],
                'description': 'RDS database support',
                'template_id': 'general_support'
            },
            'networking': {
                'keywords': [
                    'vpc', 'subnet', 'security group', 'network acl', 'route table',
                    'internet gateway', 'nat gateway', 'network', 'connectivity'
                ],
                'services': ['vpc', 'networking'],
                'description': 'VPC and networking support',
                'template_id': 'general_support'
            },
            'iam_security': {
                'keywords': [
                    'iam', 'permission', 'access denied', 'policy', 'role',
                    'user', 'authentication', 'authorization', 'security'
                ],
                'services': ['iam', 'security'],
                'description': 'IAM and security support',
                'template_id': 'general_support'
            },
            'billing_cost': {
                'keywords': [
                    'billing', 'cost', 'charge', 'invoice', 'pricing',
                    'cost explorer', 'budget', 'free tier'
                ],
                'services': ['billing', 'cost'],
                'description': 'Billing and cost support',
                'template_id': 'general_support',
                'escalation_required': True
            },
            'account_management': {
                'keywords': [
                    'account', 'organization', 'consolidated billing',
                    'service limit', 'quota', 'support plan'
                ],
                'services': ['account'],
                'description': 'Account management support',
                'template_id': 'general_support',
                'escalation_required': True
            }
        }
    
    def detect_intent(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, any]:
        """
        Detect intent from user query.
        
        Args:
            query: User query text
            conversation_history: Optional conversation history for context
            
        Returns:
            Dictionary with detected intent and confidence
        """
        try:
            # Analyze query with Comprehend
            entities = self._detect_entities(query)
            key_phrases = self._detect_key_phrases(query)
            sentiment = self._detect_sentiment(query)
            
            # Pattern-based intent detection
            intent_scores = self._calculate_intent_scores(query, entities, key_phrases)
            
            # Get top intent
            top_intent = max(intent_scores.items(), key=lambda x: x[1]) if intent_scores else ('general_support', 0.5)
            intent_name, confidence = top_intent
            
            # Determine if clarification is needed
            needs_clarification = confidence < self.clarification_threshold
            is_confident = confidence >= self.confidence_threshold
            
            # Get intent details
            intent_details = self.intent_patterns.get(intent_name, {})
            
            result = {
                'intent': intent_name,
                'confidence': confidence,
                'is_confident': is_confident,
                'needs_clarification': needs_clarification,
                'template_id': intent_details.get('template_id', 'general_support'),
                'description': intent_details.get('description', 'General support'),
                'escalation_required': intent_details.get('escalation_required', False),
                'detected_services': intent_details.get('services', []),
                'sentiment': sentiment,
                'entities': entities,
                'key_phrases': key_phrases,
                'alternative_intents': [
                    {'intent': intent, 'confidence': score}
                    for intent, score in sorted(
                        intent_scores.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[1:4]  # Top 3 alternatives
                ]
            }
            
            logger.info(f"Detected intent: {intent_name} (confidence: {confidence:.2f})")
            return result
            
        except ClientError as e:
            logger.error(f"Error detecting intent: {e}")
            return {
                'intent': 'general_support',
                'confidence': 0.5,
                'is_confident': False,
                'needs_clarification': True,
                'template_id': 'general_support',
                'error': str(e)
            }
    
    def _detect_entities(self, text: str) -> List[Dict]:
        """Detect entities using Amazon Comprehend."""
        try:
            response = self.comprehend.detect_entities(
                Text=text,
                LanguageCode='en'
            )
            return response.get('Entities', [])
        except ClientError as e:
            logger.warning(f"Error detecting entities: {e}")
            return []
    
    def _detect_key_phrases(self, text: str) -> List[Dict]:
        """Detect key phrases using Amazon Comprehend."""
        try:
            response = self.comprehend.detect_key_phrases(
                Text=text,
                LanguageCode='en'
            )
            return response.get('KeyPhrases', [])
        except ClientError as e:
            logger.warning(f"Error detecting key phrases: {e}")
            return []
    
    def _detect_sentiment(self, text: str) -> Dict:
        """Detect sentiment using Amazon Comprehend."""
        try:
            response = self.comprehend.detect_sentiment(
                Text=text,
                LanguageCode='en'
            )
            return {
                'sentiment': response.get('Sentiment'),
                'scores': response.get('SentimentScore', {})
            }
        except ClientError as e:
            logger.warning(f"Error detecting sentiment: {e}")
            return {'sentiment': 'NEUTRAL', 'scores': {}}
    
    def _calculate_intent_scores(
        self,
        query: str,
        entities: List[Dict],
        key_phrases: List[Dict]
    ) -> Dict[str, float]:
        """Calculate confidence scores for each intent."""
        query_lower = query.lower()
        scores = {}
        
        # Extract text from entities and key phrases
        entity_texts = [e['Text'].lower() for e in entities]
        phrase_texts = [p['Text'].lower() for p in key_phrases]
        all_texts = [query_lower] + entity_texts + phrase_texts
        
        # Score each intent
        for intent_name, intent_info in self.intent_patterns.items():
            score = 0.0
            keyword_count = 0
            
            for keyword in intent_info['keywords']:
                keyword_lower = keyword.lower()
                
                # Check in query (highest weight)
                if keyword_lower in query_lower:
                    score += 1.0
                    keyword_count += 1
                
                # Check in entities (medium weight)
                elif any(keyword_lower in entity for entity in entity_texts):
                    score += 0.7
                    keyword_count += 1
                
                # Check in key phrases (lower weight)
                elif any(keyword_lower in phrase for phrase in phrase_texts):
                    score += 0.5
                    keyword_count += 1
            
            # Normalize score
            if keyword_count > 0:
                normalized_score = min(score / len(intent_info['keywords']), 1.0)
                # Boost score if multiple keywords matched
                boost = min(keyword_count / 3, 0.3)
                scores[intent_name] = min(normalized_score + boost, 1.0)
        
        return scores
    
    def generate_clarification_question(self, intent_result: Dict) -> str:
        """
        Generate a clarification question when intent is unclear.
        
        Args:
            intent_result: Result from detect_intent
            
        Returns:
            Clarification question
        """
        confidence = intent_result.get('confidence', 0)
        intent = intent_result.get('intent', 'general_support')
        alternatives = intent_result.get('alternative_intents', [])
        
        if confidence < 0.3:
            # Very uncertain
            return (
                "I'd like to help you with your AWS question. To provide the most "
                "accurate assistance, could you please provide more details about:\n"
                "- Which AWS service you're working with?\n"
                "- What specific issue or task you're trying to accomplish?\n"
                "- Any error messages you're seeing?"
            )
        elif confidence < self.clarification_threshold:
            # Somewhat uncertain, ask about top alternatives
            if len(alternatives) >= 2:
                alt1 = alternatives[0]['intent'].replace('_', ' ').title()
                alt2 = alternatives[1]['intent'].replace('_', ' ').title()
                
                return (
                    f"I want to make sure I understand your question correctly. "
                    f"Are you asking about:\n"
                    f"A) {alt1}\n"
                    f"B) {alt2}\n"
                    f"C) Something else (please specify)\n\n"
                    f"Or feel free to rephrase your question with more details."
                )
        
        # Moderate confidence but needs confirmation
        intent_desc = self.intent_patterns.get(intent, {}).get('description', intent)
        return (
            f"I understand you're asking about {intent_desc}. "
            f"To help you better, could you provide more specific details about "
            f"what you're trying to accomplish or the issue you're experiencing?"
        )
    
    def requires_escalation(self, intent_result: Dict) -> Tuple[bool, str]:
        """
        Check if the intent requires human escalation.
        
        Args:
            intent_result: Result from detect_intent
            
        Returns:
            Tuple of (requires_escalation, reason)
        """
        intent = intent_result.get('intent')
        sentiment = intent_result.get('sentiment', {})
        
        # Check if intent explicitly requires escalation
        if intent_result.get('escalation_required'):
            return True, f"Intent '{intent}' requires human support"
        
        # Check for very negative sentiment (angry customer)
        if sentiment.get('sentiment') == 'NEGATIVE':
            negative_score = sentiment.get('scores', {}).get('Negative', 0)
            if negative_score > 0.85:
                return True, "High negative sentiment detected - customer may be frustrated"
        
        # Check for low confidence across all intents
        if intent_result.get('confidence', 0) < 0.3:
            return True, "Unable to determine intent with sufficient confidence"
        
        return False, ""


