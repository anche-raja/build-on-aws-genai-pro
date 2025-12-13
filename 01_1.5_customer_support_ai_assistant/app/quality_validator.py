"""
Quality Validator

Validates AI assistant responses for quality, accuracy, and adherence
to expected output formats.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QualityValidator:
    """Validates response quality and formats."""
    
    def __init__(self):
        """Initialize the Quality Validator."""
        self.validation_rules = self._load_validation_rules()
        self.expected_patterns = self._load_expected_patterns()
    
    def _load_validation_rules(self) -> Dict[str, Dict]:
        """Load quality validation rules."""
        return {
            'completeness': {
                'min_length': 100,
                'required_elements': [
                    'acknowledgment',  # Should acknowledge user's issue
                    'guidance',  # Should provide guidance or steps
                    'next_steps'  # Should suggest next steps
                ]
            },
            'structure': {
                'has_greeting': False,  # Optional greeting
                'has_sections': False,  # Optional sectioning
                'has_summary': True,  # Should have summary of next steps
                'max_length': 3000  # Maximum reasonable length
            },
            'accuracy': {
                'has_aws_docs_link': False,  # Optional but good to have
                'no_placeholders': True,  # Should not have [PLACEHOLDER] text
                'no_code_errors': True  # Code snippets should be valid
            },
            'tone': {
                'professional': True,
                'empathetic': True,
                'clear': True
            }
        }
    
    def _load_expected_patterns(self) -> Dict[str, str]:
        """Load patterns for expected response elements."""
        return {
            'acknowledgment': r'(understand|see|notice|recognize|thank you|thanks|i can help)',
            'next_steps': r'(next step|you should|please|recommend|suggest|you can|try)',
            'question': r'\?',
            'documentation_link': r'https?://(?:docs\.aws\.amazon\.com|aws\.amazon\.com/)',
            'code_block': r'```[\s\S]*?```',
            'placeholder': r'\[.*?\]|\{.*?\}|TODO|FIXME|XXX',
            'aws_service': r'\b(EC2|S3|Lambda|RDS|DynamoDB|CloudWatch|IAM|VPC)\b'
        }
    
    def validate_response(
        self,
        response: str,
        query: str,
        intent: Optional[str] = None,
        expected_criteria: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Validate a response against quality criteria.
        
        Args:
            response: AI-generated response
            query: Original user query
            intent: Detected intent
            expected_criteria: Optional custom validation criteria
            
        Returns:
            Validation result with score and issues
        """
        issues = []
        warnings = []
        score = 100.0
        
        # Check completeness
        completeness_result = self._check_completeness(response)
        if not completeness_result['valid']:
            issues.extend(completeness_result['issues'])
            score -= completeness_result['penalty']
        else:
            warnings.extend(completeness_result.get('warnings', []))
        
        # Check structure
        structure_result = self._check_structure(response)
        if not structure_result['valid']:
            issues.extend(structure_result['issues'])
            score -= structure_result['penalty']
        else:
            warnings.extend(structure_result.get('warnings', []))
        
        # Check accuracy
        accuracy_result = self._check_accuracy(response)
        if not accuracy_result['valid']:
            issues.extend(accuracy_result['issues'])
            score -= accuracy_result['penalty']
        
        # Check relevance to query
        relevance_result = self._check_relevance(response, query, intent)
        if not relevance_result['valid']:
            warnings.extend(relevance_result['warnings'])
            score -= relevance_result['penalty']
        
        # Check tone
        tone_result = self._check_tone(response)
        if not tone_result['valid']:
            warnings.extend(tone_result['warnings'])
            score -= tone_result['penalty']
        
        # Overall validation
        is_valid = score >= 70.0 and len(issues) == 0
        
        result = {
            'is_valid': is_valid,
            'score': max(0, score),
            'issues': issues,
            'warnings': warnings,
            'details': {
                'completeness': completeness_result,
                'structure': structure_result,
                'accuracy': accuracy_result,
                'relevance': relevance_result,
                'tone': tone_result
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Response validation score: {result['score']:.2f}")
        return result
    
    def _check_completeness(self, response: str) -> Dict[str, Any]:
        """Check if response is complete and substantive."""
        issues = []
        warnings = []
        penalty = 0
        
        # Check minimum length
        if len(response) < self.validation_rules['completeness']['min_length']:
            issues.append(f"Response too short: {len(response)} chars")
            penalty += 30
        
        # Check for acknowledgment
        if not re.search(
            self.expected_patterns['acknowledgment'],
            response,
            re.IGNORECASE
        ):
            warnings.append("Response lacks acknowledgment of user's issue")
            penalty += 5
        
        # Check for next steps
        if not re.search(
            self.expected_patterns['next_steps'],
            response,
            re.IGNORECASE
        ):
            issues.append("Response lacks clear next steps or guidance")
            penalty += 20
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'penalty': penalty
        }
    
    def _check_structure(self, response: str) -> Dict[str, Any]:
        """Check response structure and formatting."""
        issues = []
        warnings = []
        penalty = 0
        
        # Check maximum length
        max_length = self.validation_rules['structure']['max_length']
        if len(response) > max_length:
            issues.append(f"Response too long: {len(response)} chars (max: {max_length})")
            penalty += 10
        
        # Check for sections/organization (using line breaks as indicator)
        lines = response.split('\n')
        if len(lines) < 3:
            warnings.append("Response could benefit from better organization")
            penalty += 3
        
        # Check for numbered or bulleted lists (good practice)
        has_list = bool(re.search(r'^\s*[\d\-\*•]\s+', response, re.MULTILINE))
        if not has_list and len(response) > 500:
            warnings.append("Long response could benefit from lists or bullet points")
            penalty += 2
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'penalty': penalty
        }
    
    def _check_accuracy(self, response: str) -> Dict[str, Any]:
        """Check for accuracy issues."""
        issues = []
        penalty = 0
        
        # Check for placeholders
        placeholders = re.findall(self.expected_patterns['placeholder'], response)
        if placeholders:
            issues.append(f"Response contains placeholders: {placeholders[:3]}")
            penalty += 40  # This is a serious issue
        
        # Check for broken code blocks
        code_blocks = re.findall(r'```', response)
        if len(code_blocks) % 2 != 0:
            issues.append("Unmatched code block markers")
            penalty += 15
        
        # Check for common errors
        error_patterns = [
            (r'http://docs\.aws', "Should use HTTPS for AWS docs"),
            (r'<YOUR_.*?>', "Contains placeholder tags"),
            (r'\$\{.*?\}', "Contains template variables")
        ]
        
        for pattern, message in error_patterns:
            if re.search(pattern, response):
                issues.append(message)
                penalty += 10
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'penalty': penalty
        }
    
    def _check_relevance(
        self,
        response: str,
        query: str,
        intent: Optional[str]
    ) -> Dict[str, Any]:
        """Check if response is relevant to the query."""
        warnings = []
        penalty = 0
        
        # Extract key terms from query
        query_terms = set(re.findall(r'\b\w+\b', query.lower()))
        query_terms = {t for t in query_terms if len(t) > 3}  # Filter short words
        
        # Check if response mentions key AWS services from query
        response_lower = response.lower()
        aws_services = ['ec2', 's3', 'lambda', 'rds', 'dynamodb', 'vpc', 
                       'iam', 'cloudwatch', 'cloudformation', 'elb']
        
        query_services = [s for s in aws_services if s in query.lower()]
        if query_services:
            response_mentions = [s for s in query_services if s in response_lower]
            if not response_mentions:
                warnings.append(f"Response may not address mentioned services: {query_services}")
                penalty += 10
        
        return {
            'valid': True,  # Warnings don't invalidate
            'warnings': warnings,
            'penalty': penalty
        }
    
    def _check_tone(self, response: str) -> Dict[str, Any]:
        """Check if response has appropriate tone."""
        warnings = []
        penalty = 0
        
        # Check for overly technical jargon without explanation
        jargon_terms = ['api', 'cli', 'sdk', 'vpc', 'cidr', 'arn', 'iam']
        jargon_count = sum(1 for term in jargon_terms if term in response.lower())
        
        if jargon_count > 5 and len(response) < 500:
            warnings.append("Response may be too technical - consider simplifying")
            penalty += 5
        
        # Check for empathy indicators
        empathy_indicators = [
            'understand', 'help', 'assist', 'sorry', 'apologize',
            'i see', 'i notice', 'i can help'
        ]
        
        has_empathy = any(indicator in response.lower() for indicator in empathy_indicators)
        if not has_empathy:
            warnings.append("Response could be more empathetic")
            penalty += 3
        
        return {
            'valid': True,
            'warnings': warnings,
            'penalty': penalty
        }
    
    def validate_against_test_cases(
        self,
        response: str,
        test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate response against specific test case criteria.
        
        Args:
            response: AI-generated response
            test_case: Test case with expected criteria
            
        Returns:
            Validation result
        """
        issues = []
        
        # Check required keywords
        if 'required_keywords' in test_case:
            for keyword in test_case['required_keywords']:
                if keyword.lower() not in response.lower():
                    issues.append(f"Missing required keyword: {keyword}")
        
        # Check prohibited keywords
        if 'prohibited_keywords' in test_case:
            for keyword in test_case['prohibited_keywords']:
                if keyword.lower() in response.lower():
                    issues.append(f"Contains prohibited keyword: {keyword}")
        
        # Check expected format
        if 'expected_format' in test_case:
            format_type = test_case['expected_format']
            if format_type == 'numbered_list' and not re.search(r'^\d+\.', response, re.MULTILINE):
                issues.append("Expected numbered list format")
            elif format_type == 'code_block' and '```' not in response:
                issues.append("Expected code block")
        
        # Check minimum steps (for troubleshooting)
        if 'min_steps' in test_case:
            steps = re.findall(r'^\d+\.', response, re.MULTILINE)
            if len(steps) < test_case['min_steps']:
                issues.append(f"Expected at least {test_case['min_steps']} steps, found {len(steps)}")
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'test_case_id': test_case.get('id', 'unknown')
        }
    
    def generate_improvement_suggestions(
        self,
        validation_result: Dict[str, Any]
    ) -> List[str]:
        """
        Generate suggestions for improving the response.
        
        Args:
            validation_result: Result from validate_response
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        if validation_result['score'] < 70:
            suggestions.append("Consider regenerating the response with a different approach")
        
        if validation_result['issues']:
            suggestions.append("Address critical issues: " + "; ".join(validation_result['issues'][:3]))
        
        details = validation_result.get('details', {})
        
        # Completeness suggestions
        if details.get('completeness', {}).get('warnings'):
            suggestions.append("Add clear acknowledgment of the user's issue at the start")
        
        # Structure suggestions
        if details.get('structure', {}).get('warnings'):
            suggestions.append("Improve organization with sections or bullet points")
        
        # Tone suggestions
        if details.get('tone', {}).get('warnings'):
            suggestions.append("Use more empathetic and supportive language")
        
        return suggestions



