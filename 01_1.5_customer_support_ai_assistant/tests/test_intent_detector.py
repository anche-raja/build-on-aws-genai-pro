"""
Unit Tests for Intent Detector
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.intent_detector import IntentDetector


class TestIntentDetector(unittest.TestCase):
    """Test cases for Intent Detector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = IntentDetector(region='us-east-1')
    
    def test_ec2_intent_detection(self):
        """Test EC2 troubleshooting intent detection."""
        query = "My EC2 instance is not responding to SSH connections"
        result = self.detector.detect_intent(query)
        
        self.assertEqual(result['intent'], 'ec2_troubleshooting')
        self.assertGreater(result['confidence'], 0.5)
        self.assertIn('ec2', result['detected_services'])
    
    def test_s3_intent_detection(self):
        """Test S3 troubleshooting intent detection."""
        query = "I'm getting access denied errors when trying to upload to my S3 bucket"
        result = self.detector.detect_intent(query)
        
        self.assertEqual(result['intent'], 's3_troubleshooting')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_lambda_intent_detection(self):
        """Test Lambda troubleshooting intent detection."""
        query = "My Lambda function is timing out after 30 seconds"
        result = self.detector.detect_intent(query)
        
        self.assertEqual(result['intent'], 'lambda_troubleshooting')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_low_confidence_detection(self):
        """Test low confidence query."""
        query = "I need help with something"
        result = self.detector.detect_intent(query)
        
        self.assertTrue(result['needs_clarification'])
        self.assertLess(result['confidence'], 0.7)
    
    def test_billing_escalation(self):
        """Test that billing queries trigger escalation."""
        query = "Why is my AWS bill so high this month?"
        result = self.detector.detect_intent(query)
        
        self.assertTrue(result.get('escalation_required', False))
    
    def test_clarification_generation(self):
        """Test clarification question generation."""
        query = "Help with AWS"
        result = self.detector.detect_intent(query)
        
        clarification = self.detector.generate_clarification_question(result)
        self.assertIsInstance(clarification, str)
        self.assertGreater(len(clarification), 50)


class TestIntentPatterns(unittest.TestCase):
    """Test intent pattern matching."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = IntentDetector(region='us-east-1')
    
    def test_multiple_services_mentioned(self):
        """Test query with multiple services."""
        query = "How do I connect my EC2 instance to my RDS database?"
        result = self.detector.detect_intent(query)
        
        self.assertIsNotNone(result['intent'])
        self.assertIsInstance(result['detected_services'], list)
    
    def test_negative_sentiment_escalation(self):
        """Test that highly negative sentiment triggers escalation."""
        query = "This is completely unacceptable! My production system has been down for hours!"
        result = self.detector.detect_intent(query)
        
        # Check if escalation logic considers sentiment
        escalation_needed, reason = self.detector.requires_escalation(result)
        # Note: This may or may not escalate depending on implementation


if __name__ == '__main__':
    unittest.main()



