"""
AWS Customer Support AI Assistant

A production-ready customer support AI assistant built with Amazon Bedrock,
implementing prompt engineering strategies and governance controls.
"""

__version__ = "1.0.0"
__author__ = "AWS GenAI Team"

from .bedrock_prompt_manager import BedrockPromptManager
from .guardrails_manager import GuardrailsManager
from .conversation_handler import ConversationHandler
from .intent_detector import IntentDetector
from .quality_validator import QualityValidator
from .feedback_collector import FeedbackCollector

__all__ = [
    "BedrockPromptManager",
    "GuardrailsManager",
    "ConversationHandler",
    "IntentDetector",
    "QualityValidator",
    "FeedbackCollector",
]


