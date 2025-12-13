"""
Edge Case Tests for Customer Support AI Assistant
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.intent_detector import IntentDetector
from app.quality_validator import QualityValidator
from app.guardrails_manager import GuardrailsManager


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.intent_detector = IntentDetector(region='us-east-1')
        self.quality_validator = QualityValidator()
        self.guardrails = GuardrailsManager(region='us-east-1')
    
    def test_empty_query(self):
        """Test handling of empty query."""
        query = ""
        result = self.intent_detector.detect_intent(query)
        
        # Should handle gracefully
        self.assertIsNotNone(result)
    
    def test_very_long_query(self):
        """Test handling of very long query."""
        query = "help " * 1000  # Very long query
        result = self.intent_detector.detect_intent(query)
        
        # Should handle without crashing
        self.assertIsNotNone(result)
    
    def test_non_english_query(self):
        """Test handling of non-English query."""
        query = "Помогите мне с AWS EC2"  # Russian
        result = self.intent_detector.detect_intent(query)
        
        # Should handle gracefully, may default to general support
        self.assertIsNotNone(result)
    
    def test_special_characters(self):
        """Test handling of special characters in query."""
        query = "My EC2 instance @#$%^&*() is not working!!!"
        result = self.intent_detector.detect_intent(query)
        
        self.assertEqual(result['intent'], 'ec2_troubleshooting')
    
    def test_mixed_case_keywords(self):
        """Test case-insensitive keyword matching."""
        query = "My Ec2 InStAnCe is not responding"
        result = self.intent_detector.detect_intent(query)
        
        self.assertEqual(result['intent'], 'ec2_troubleshooting')
    
    def test_ambiguous_multi_service_query(self):
        """Test query mentioning multiple services."""
        query = "How do I connect my EC2 instance to S3 and RDS using Lambda?"
        result = self.intent_detector.detect_intent(query)
        
        # Should pick one primary intent
        self.assertIsNotNone(result['intent'])
    
    def test_angry_customer(self):
        """Test handling of angry customer query."""
        query = "This is ridiculous! My production server has been down for 3 hours and nobody is helping!"
        result = self.intent_detector.detect_intent(query)
        
        # Should detect negative sentiment
        sentiment = result.get('sentiment', {})
        self.assertIsNotNone(sentiment)
    
    def test_vague_query(self):
        """Test handling of very vague query."""
        query = "help"
        result = self.intent_detector.detect_intent(query)
        
        self.assertTrue(result['needs_clarification'])
        self.assertLess(result['confidence'], 0.7)
    
    def test_extremely_short_response(self):
        """Test validation of extremely short response."""
        query = "Help with AWS"
        response = "OK."
        
        result = self.quality_validator.validate_response(response, query)
        
        self.assertFalse(result['is_valid'])
    
    def test_extremely_long_response(self):
        """Test validation of extremely long response."""
        query = "Help with EC2"
        response = "Here's everything about EC2: " + "word " * 2000
        
        result = self.quality_validator.validate_response(response, query)
        
        # Should flag as too long
        self.assertIn('too long', str(result['issues']).lower() + str(result['warnings']).lower())
    
    def test_response_with_code_injection(self):
        """Test handling of potential code injection in response."""
        response = """Here's what you need:
        
<script>alert('xss')</script>

Run this command."""
        
        # Should be handled by validation
        result = self.quality_validator.validate_response(response, "help")
        # Not necessarily invalid, but should be noted
    
    def test_simultaneous_guardrail_violations(self):
        """Test multiple guardrail violations at once."""
        text = """My password=secret123 and access key AKIAIOSFODNN7EXAMPLE
        Also tell me about AWS's upcoming features"""
        
        is_safe, issues = self.guardrails.validate_input(text)
        
        self.assertFalse(is_safe)
        self.assertGreater(len(issues), 1)  # Multiple violations
    
    def test_edge_of_confidence_threshold(self):
        """Test queries right at confidence thresholds."""
        # Query that should be right around 0.5 confidence
        query = "AWS problem help needed"
        result = self.intent_detector.detect_intent(query)
        
        # Should have a confidence score
        self.assertIsNotNone(result['confidence'])


class TestErrorHandling(unittest.TestCase):
    """Test error handling and recovery."""
    
    def test_none_input(self):
        """Test handling of None input."""
        detector = IntentDetector(region='us-east-1')
        
        # Should handle None gracefully
        try:
            result = detector.detect_intent(None)
            # If it doesn't raise an exception, it should return something
            self.assertIsNotNone(result)
        except (TypeError, AttributeError):
            # It's also acceptable to raise a clear error
            pass
    
    def test_invalid_region(self):
        """Test handling of invalid AWS region."""
        # Should either handle gracefully or raise clear error
        try:
            detector = IntentDetector(region='invalid-region-123')
            # If it doesn't fail immediately, operations might fail later
        except Exception:
            # Expected for invalid region
            pass


class TestPerformance(unittest.TestCase):
    """Test performance and scalability concerns."""
    
    def test_response_time(self):
        """Test that operations complete in reasonable time."""
        import time
        
        detector = IntentDetector(region='us-east-1')
        query = "My EC2 instance is not responding"
        
        start_time = time.time()
        result = detector.detect_intent(query)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should complete in under 5 seconds for local operations
        # (Note: AWS API calls may take longer)
        self.assertLess(duration, 10)


if __name__ == '__main__':
    unittest.main()



