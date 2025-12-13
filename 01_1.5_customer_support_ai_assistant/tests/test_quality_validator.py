"""
Unit Tests for Quality Validator
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.quality_validator import QualityValidator


class TestQualityValidator(unittest.TestCase):
    """Test cases for Quality Validator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = QualityValidator()
    
    def test_good_response_validation(self):
        """Test validation of a good quality response."""
        query = "My EC2 instance is not responding"
        response = """I understand you're experiencing issues with your EC2 instance not responding. Let me help you troubleshoot this.

Here are the steps to diagnose the issue:

1. Check Instance Status Checks:
   - Go to EC2 Console
   - Select your instance
   - Check the Status Checks tab

2. Verify Security Groups:
   - Ensure port 22 (SSH) is open
   - Check your IP is allowed

3. Review Network Configuration:
   - Verify the instance has a public IP
   - Check route tables

Next steps:
- Try these steps and let me know what you find
- If the issue persists, I can help you dive deeper

Would you like me to explain any of these steps in more detail?"""
        
        result = self.validator.validate_response(
            response=response,
            query=query,
            intent='ec2_troubleshooting'
        )
        
        self.assertTrue(result['is_valid'])
        self.assertGreater(result['score'], 70)
        self.assertEqual(len(result['issues']), 0)
    
    def test_too_short_response(self):
        """Test validation of too short response."""
        query = "Help with EC2"
        response = "Check the console."
        
        result = self.validator.validate_response(
            response=response,
            query=query
        )
        
        self.assertFalse(result['is_valid'])
        self.assertLess(result['score'], 70)
        self.assertGreater(len(result['issues']), 0)
    
    def test_response_with_placeholders(self):
        """Test validation of response with placeholders."""
        query = "How do I configure S3?"
        response = """To configure S3, follow these steps:
        
1. Go to [YOUR_BUCKET_NAME]
2. Set permissions to [TODO: Add permissions]
3. Configure ${REGION} settings

This should help."""
        
        result = self.validator.validate_response(
            response=response,
            query=query
        )
        
        self.assertFalse(result['is_valid'])
        self.assertIn('placeholders', str(result['issues']).lower())
    
    def test_response_missing_next_steps(self):
        """Test validation of response without clear next steps."""
        query = "EC2 instance issue"
        response = """EC2 instances can have various issues. There are many things 
        that could go wrong with an instance. Sometimes it's networking, sometimes 
        it's the instance itself. These things happen."""
        
        result = self.validator.validate_response(
            response=response,
            query=query
        )
        
        self.assertLess(result['score'], 90)
        # Should have warnings about missing guidance
    
    def test_test_case_validation(self):
        """Test validation against specific test case criteria."""
        response = """Here are the troubleshooting steps:

1. Check instance status
2. Verify security groups
3. Review logs
4. Test connectivity"""
        
        test_case = {
            'id': 'test-1',
            'required_keywords': ['status', 'security'],
            'prohibited_keywords': ['password', 'secret key'],
            'expected_format': 'numbered_list',
            'min_steps': 3
        }
        
        result = self.validator.validate_against_test_cases(
            response=response,
            test_case=test_case
        )
        
        self.assertTrue(result['passed'])
    
    def test_improvement_suggestions(self):
        """Test generation of improvement suggestions."""
        validation_result = {
            'is_valid': False,
            'score': 50,
            'issues': ['Response too short', 'Missing next steps'],
            'warnings': ['Could be more empathetic'],
            'details': {
                'completeness': {'warnings': ['Lacks acknowledgment']},
                'structure': {'warnings': ['Poor organization']},
                'tone': {'warnings': ['Not empathetic']}
            }
        }
        
        suggestions = self.validator.generate_improvement_suggestions(validation_result)
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)


class TestValidationRules(unittest.TestCase):
    """Test individual validation rules."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = QualityValidator()
    
    def test_completeness_check(self):
        """Test completeness validation."""
        short_response = "Check the logs."
        result = self.validator._check_completeness(short_response)
        self.assertFalse(result['valid'])
        
        complete_response = """I understand your issue. Here's what you should do:
        
1. Check the instance status in the console
2. Verify your security group settings
3. Review the system logs
4. Try to connect using Session Manager

Please let me know if any of these steps don't work, and I'll help you further."""
        
        result = self.validator._check_completeness(complete_response)
        self.assertTrue(result['valid'])
    
    def test_accuracy_check(self):
        """Test accuracy validation."""
        response_with_errors = "Check http://docs.aws.amazon.com and set ${YOUR_CONFIG}"
        result = self.validator._check_accuracy(response_with_errors)
        self.assertFalse(result['valid'])


if __name__ == '__main__':
    unittest.main()


