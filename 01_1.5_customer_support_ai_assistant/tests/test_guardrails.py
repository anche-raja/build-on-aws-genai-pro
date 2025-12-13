"""
Unit Tests for Guardrails Manager
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.guardrails_manager import GuardrailsManager


class TestGuardrailsManager(unittest.TestCase):
    """Test cases for Guardrails Manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.guardrails = GuardrailsManager(region='us-east-1')
    
    def test_detect_aws_access_key(self):
        """Test detection of AWS access key in input."""
        text = "My access key is AKIAIOSFODNN7EXAMPLE"
        is_safe, issues = self.guardrails.validate_input(text)
        
        self.assertFalse(is_safe)
        self.assertGreater(len(issues), 0)
        self.assertIn('Access Key', str(issues))
    
    def test_detect_password(self):
        """Test detection of password in input."""
        text = "I tried password=MySecretPass123 but it didn't work"
        is_safe, issues = self.guardrails.validate_input(text)
        
        self.assertFalse(is_safe)
        self.assertIn('Password', str(issues))
    
    def test_detect_private_key(self):
        """Test detection of private key."""
        text = """Here's my key:
        -----BEGIN RSA PRIVATE KEY-----
        MIIEpAIBAAKCAQEA...
        """
        is_safe, issues = self.guardrails.validate_input(text)
        
        self.assertFalse(is_safe)
    
    def test_safe_input(self):
        """Test validation of safe input."""
        text = "My EC2 instance is not responding to ping"
        is_safe, issues = self.guardrails.validate_input(text)
        
        self.assertTrue(is_safe)
        self.assertEqual(len(issues), 0)
    
    def test_blocked_topic_future_features(self):
        """Test detection of blocked topic (future features)."""
        text = "When will AWS release the new feature we discussed?"
        is_safe, issues = self.guardrails.validate_input(text)
        
        # Should flag future features topic
        self.assertFalse(is_safe)
    
    def test_output_validation_future_commitment(self):
        """Test output validation for future commitments."""
        output = "AWS will launch this feature next month. It will be available in Q2."
        is_safe, issues = self.guardrails.validate_output(output)
        
        self.assertFalse(is_safe)
        self.assertIn('future commitment', str(issues).lower())
    
    def test_output_validation_competitor_disparagement(self):
        """Test output validation for competitor disparagement."""
        output = "Azure is bad and you shouldn't use it. Google Cloud has many problems."
        is_safe, issues = self.guardrails.validate_output(output)
        
        self.assertFalse(is_safe)
    
    def test_output_validation_safe(self):
        """Test validation of safe output."""
        output = """To troubleshoot your EC2 instance:
        
1. Check the instance status checks
2. Verify security group rules
3. Review CloudWatch logs

Let me know if you need help with any of these steps."""
        
        is_safe, issues = self.guardrails.validate_output(output)
        
        self.assertTrue(is_safe)
        self.assertEqual(len(issues), 0)
    
    def test_apply_guardrails(self):
        """Test applying guardrails to both input and output."""
        prompt = "How do I configure my EC2 instance?"
        response = "Here's how to configure it: [steps here]"
        
        result = self.guardrails.apply_guardrails(prompt, response)
        
        self.assertIn('input_safe', result)
        self.assertIn('output_safe', result)
        self.assertIn('overall_safe', result)
        self.assertTrue(result['overall_safe'])
    
    def test_safe_response_generation(self):
        """Test generation of safe fallback responses."""
        input_issues = ['Detected AWS Access Key: AWS Access Key ID']
        output_issues = []
        
        safe_response = self.guardrails._generate_safe_response(
            input_issues, output_issues
        )
        
        self.assertIsInstance(safe_response, str)
        self.assertIn('credentials', safe_response.lower())


class TestTopicDetection(unittest.TestCase):
    """Test topic appropriateness detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.guardrails = GuardrailsManager(region='us-east-1')
    
    def test_assess_appropriateness(self):
        """Test assessment of content appropriateness."""
        # Note: This requires AWS Comprehend, so it may need mocking for unit tests
        # For now, we'll test the structure
        entities_response = {'Entities': []}
        sentiment_response = {
            'Sentiment': 'NEUTRAL',
            'SentimentScore': {
                'Positive': 0.1,
                'Negative': 0.1,
                'Neutral': 0.8,
                'Mixed': 0.0
            }
        }
        
        is_appropriate = self.guardrails._assess_appropriateness(
            entities_response,
            sentiment_response
        )
        
        self.assertTrue(is_appropriate)


if __name__ == '__main__':
    unittest.main()


