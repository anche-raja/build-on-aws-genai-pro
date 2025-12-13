"""
Guardrails Manager

Implements Amazon Bedrock Guardrails to prevent inappropriate responses
and ensure responsible AI usage.
"""

import boto3
import json
import re
import logging
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GuardrailsManager:
    """Manages guardrails for responsible AI usage."""
    
    def __init__(
        self,
        region: str = "us-east-1",
        guardrail_id: Optional[str] = None,
        guardrail_version: Optional[str] = None
    ):
        """
        Initialize the Guardrails Manager.
        
        Args:
            region: AWS region
            guardrail_id: Bedrock Guardrail ID
            guardrail_version: Guardrail version
        """
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        self.comprehend = boto3.client('comprehend', region_name=region)
        
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        
        # Define guardrail rules
        self.sensitive_patterns = self._load_sensitive_patterns()
        self.blocked_topics = self._load_blocked_topics()
        self.competitor_guidelines = self._load_competitor_guidelines()
    
    def _load_sensitive_patterns(self) -> List[Dict[str, str]]:
        """Load patterns for detecting sensitive information."""
        return [
            {
                'name': 'AWS Access Key',
                'pattern': r'AKIA[0-9A-Z]{16}',
                'description': 'AWS Access Key ID'
            },
            {
                'name': 'AWS Secret Key',
                'pattern': r'[A-Za-z0-9/+=]{40}',
                'description': 'Potential AWS Secret Access Key',
                'context_required': True  # Requires additional context
            },
            {
                'name': 'Password',
                'pattern': r'\b(password|passwd|pwd)\s*[:=]\s*\S+',
                'description': 'Password in plain text',
                'case_insensitive': True
            },
            {
                'name': 'Private Key',
                'pattern': r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
                'description': 'Private key material'
            },
            {
                'name': 'API Key',
                'pattern': r'\b(api[_-]?key|apikey)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}',
                'description': 'Generic API key',
                'case_insensitive': True
            }
        ]
    
    def _load_blocked_topics(self) -> List[Dict[str, any]]:
        """Load topics that should not be discussed."""
        return [
            {
                'topic': 'future_features',
                'keywords': [
                    'roadmap', 'upcoming', 'will be released', 'future release',
                    'planning to launch', 'next version', 'soon', 'future plans'
                ],
                'response': (
                    "I cannot make commitments or discuss specific future AWS features "
                    "or roadmap items. I recommend checking the AWS What's New blog "
                    "(https://aws.amazon.com/new/) and AWS re:Invent announcements for "
                    "information about new services and features."
                )
            },
            {
                'topic': 'account_credentials',
                'keywords': [
                    'access key', 'secret key', 'password', 'credentials',
                    'login info', 'authentication token'
                ],
                'response': (
                    "I cannot provide, request, or handle AWS account credentials. "
                    "Please never share your access keys, passwords, or other credentials "
                    "in this chat. If you've accidentally exposed credentials, please rotate "
                    "them immediately through the AWS Console."
                )
            },
            {
                'topic': 'direct_account_modification',
                'keywords': [
                    'delete my', 'modify my account', 'change my billing',
                    'cancel my subscription', 'close my account'
                ],
                'response': (
                    "I cannot directly modify AWS accounts or resources. For account "
                    "changes, billing modifications, or account closure, please use the "
                    "AWS Console or contact AWS Support directly through your support plan."
                )
            }
        ]
    
    def _load_competitor_guidelines(self) -> Dict[str, str]:
        """Load guidelines for discussing competitors."""
        return {
            'policy': (
                "When discussing competitors, remain professional, factual, and neutral. "
                "Focus on AWS services and how they can meet the customer's needs rather "
                "than disparaging other providers."
            ),
            'competitors': [
                'azure', 'microsoft cloud', 'google cloud', 'gcp',
                'oracle cloud', 'alibaba cloud', 'ibm cloud'
            ],
            'approved_response_pattern': (
                "I can help you understand AWS services and their capabilities. "
                "While I'm focused on AWS solutions, I can provide factual comparisons "
                "to help you make informed decisions. What specific requirements or "
                "use cases would you like to discuss?"
            )
        }
    
    def validate_input(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate user input for sensitive information and blocked topics.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (is_safe, list_of_issues)
        """
        issues = []
        
        # Check for sensitive patterns
        for pattern_info in self.sensitive_patterns:
            pattern = pattern_info['pattern']
            flags = re.IGNORECASE if pattern_info.get('case_insensitive') else 0
            
            if re.search(pattern, text, flags):
                issues.append(f"Detected {pattern_info['name']}: {pattern_info['description']}")
                logger.warning(f"Sensitive data detected: {pattern_info['name']}")
        
        # Check for blocked topics
        text_lower = text.lower()
        for topic_info in self.blocked_topics:
            for keyword in topic_info['keywords']:
                if keyword in text_lower:
                    issues.append(f"Blocked topic detected: {topic_info['topic']}")
                    logger.warning(f"Blocked topic detected: {topic_info['topic']}")
                    break
        
        is_safe = len(issues) == 0
        return is_safe, issues
    
    def validate_output(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate model output for sensitive information.
        
        Args:
            text: Model output text
            
        Returns:
            Tuple of (is_safe, list_of_issues)
        """
        issues = []
        
        # Check for sensitive patterns in output
        for pattern_info in self.sensitive_patterns:
            pattern = pattern_info['pattern']
            flags = re.IGNORECASE if pattern_info.get('case_insensitive') else 0
            
            if re.search(pattern, text, flags):
                issues.append(f"Output contains {pattern_info['name']}")
                logger.error(f"Model output contains sensitive data: {pattern_info['name']}")
        
        # Check for future commitments
        future_indicators = [
            r'we will (launch|release|add)',
            r'coming soon',
            r'in the (next|upcoming) (version|release)',
            r'(aws|amazon) (is|will be) planning'
        ]
        
        for indicator in future_indicators:
            if re.search(indicator, text, re.IGNORECASE):
                issues.append("Output contains future commitment")
                logger.warning("Output contains potential future commitment")
                break
        
        # Check for competitor disparagement
        negative_patterns = [
            r'(azure|gcp|google cloud).*(bad|worse|inferior|poor)',
            r'(azure|gcp|google cloud).*(should not|shouldn\'t|avoid)',
            r'(azure|gcp|google cloud).*(problem|issue|flaw)'
        ]
        
        for pattern in negative_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append("Output may contain competitor disparagement")
                logger.warning("Output contains potential competitor disparagement")
                break
        
        is_safe = len(issues) == 0
        return is_safe, issues
    
    def apply_guardrails(
        self,
        prompt: str,
        model_response: str
    ) -> Dict[str, any]:
        """
        Apply guardrails to both input and output.
        
        Args:
            prompt: User input prompt
            model_response: Model generated response
            
        Returns:
            Dictionary with validation results
        """
        # Validate input
        input_safe, input_issues = self.validate_input(prompt)
        
        # Validate output
        output_safe, output_issues = self.validate_output(model_response)
        
        result = {
            'input_safe': input_safe,
            'input_issues': input_issues,
            'output_safe': output_safe,
            'output_issues': output_issues,
            'overall_safe': input_safe and output_safe
        }
        
        # If there are issues, generate safe response
        if not result['overall_safe']:
            result['safe_response'] = self._generate_safe_response(
                input_issues, output_issues
            )
        
        return result
    
    def _generate_safe_response(
        self,
        input_issues: List[str],
        output_issues: List[str]
    ) -> str:
        """Generate a safe fallback response when guardrails are triggered."""
        
        if input_issues:
            # Check if it's a credentials issue
            if any('credentials' in issue.lower() or 'key' in issue.lower() 
                   for issue in input_issues):
                return (
                    "I noticed your message may contain sensitive credentials. "
                    "Please never share AWS access keys, secret keys, passwords, or "
                    "other credentials in this chat. If you've accidentally exposed "
                    "credentials, please rotate them immediately through the AWS Console. "
                    "I'm here to help with your technical question - could you rephrase "
                    "without including sensitive information?"
                )
            
            # Check for blocked topics
            for topic_info in self.blocked_topics:
                if any(topic_info['topic'] in issue.lower() for issue in input_issues):
                    return topic_info['response']
        
        if output_issues:
            return (
                "I apologize, but I need to refine my response to ensure it meets our "
                "guidelines. Let me provide you with accurate information about AWS services "
                "and how they can help with your needs. Could you provide more details about "
                "your specific use case or issue?"
            )
        
        return (
            "I want to make sure I provide safe and accurate information. "
            "Could you please rephrase your question or provide more context?"
        )
    
    def check_topic_appropriateness(self, text: str) -> Dict[str, any]:
        """
        Use Amazon Comprehend to detect topics and assess appropriateness.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with topic analysis
        """
        try:
            # Detect entities
            entities_response = self.comprehend.detect_entities(
                Text=text,
                LanguageCode='en'
            )
            
            # Detect sentiment
            sentiment_response = self.comprehend.detect_sentiment(
                Text=text,
                LanguageCode='en'
            )
            
            # Detect key phrases
            phrases_response = self.comprehend.detect_key_phrases(
                Text=text,
                LanguageCode='en'
            )
            
            return {
                'entities': entities_response.get('Entities', []),
                'sentiment': sentiment_response.get('Sentiment'),
                'sentiment_scores': sentiment_response.get('SentimentScore'),
                'key_phrases': phrases_response.get('KeyPhrases', []),
                'is_appropriate': self._assess_appropriateness(
                    entities_response, sentiment_response
                )
            }
            
        except ClientError as e:
            logger.error(f"Error in topic analysis: {e}")
            return {
                'error': str(e),
                'is_appropriate': True  # Fail open
            }
    
    def _assess_appropriateness(
        self,
        entities_response: Dict,
        sentiment_response: Dict
    ) -> bool:
        """Assess if content is appropriate based on detected topics and sentiment."""
        
        # Check for extremely negative sentiment (potential abuse)
        sentiment = sentiment_response.get('Sentiment')
        if sentiment == 'NEGATIVE':
            negative_score = sentiment_response.get('SentimentScore', {}).get('Negative', 0)
            if negative_score > 0.9:
                logger.warning("Extremely negative sentiment detected")
                # Still return True but log for monitoring
        
        return True  # Allow most content, log for review



