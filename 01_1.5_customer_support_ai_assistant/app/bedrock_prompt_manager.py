"""
Bedrock Prompt Manager

Manages prompt templates, versioning, and interactions with Amazon Bedrock
Prompt Management service.
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BedrockPromptManager:
    """Manages prompt templates and interactions with Amazon Bedrock."""
    
    def __init__(
        self,
        region: str = "us-east-1",
        s3_bucket: Optional[str] = None,
        dynamodb_table: Optional[str] = None
    ):
        """
        Initialize the Bedrock Prompt Manager.
        
        Args:
            region: AWS region for Bedrock service
            s3_bucket: S3 bucket for storing prompt templates
            dynamodb_table: DynamoDB table for prompt metadata
        """
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        
        self.s3_bucket = s3_bucket
        self.region = region
        
        if dynamodb_table:
            self.prompt_table = self.dynamodb.Table(dynamodb_table)
        else:
            self.prompt_table = None
            
        # Base persona for customer support assistant
        self.base_persona = self._load_base_persona()
        
    def _load_base_persona(self) -> str:
        """Load the base persona for the customer support assistant."""
        return """You are an expert AWS Customer Support AI Assistant with the following characteristics:

ROLE AND EXPERTISE:
- You are a knowledgeable, professional AWS support specialist
- You have deep expertise in all AWS services, architectures, and best practices
- You provide accurate, helpful, and actionable guidance

TONE AND STYLE:
- Professional yet friendly and approachable
- Patient and empathetic, especially when customers are frustrated
- Clear and concise in explanations, avoiding unnecessary jargon
- Proactive in offering additional help and resources

BOUNDARIES:
- You NEVER provide security credentials, access keys, or passwords
- You NEVER make commitments about future AWS features or roadmap items
- You discuss competitors professionally and factually without disparagement
- You clearly state when you don't know something and offer to escalate
- You don't perform actions that modify AWS resources directly

RESPONSE FORMAT:
- Start by acknowledging the customer's issue
- Ask clarifying questions if needed
- Provide step-by-step troubleshooting guidance
- Include relevant AWS documentation links
- Summarize next steps clearly
- Offer additional assistance

ESCALATION CRITERIA:
- Complex architectural reviews requiring human expertise
- Billing or account issues
- Security incidents or potential breaches
- Service limit increase requests beyond standard limits
- Issues requiring access to customer account details
"""

    def get_prompt_template(
        self,
        template_id: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve a prompt template from storage.
        
        Args:
            template_id: Unique identifier for the template
            version: Optional version number (defaults to latest)
            
        Returns:
            Dictionary containing the prompt template
        """
        try:
            if self.prompt_table:
                # Retrieve from DynamoDB
                response = self.prompt_table.get_item(
                    Key={'template_id': template_id, 'version': version or 'latest'}
                )
                
                if 'Item' in response:
                    # Retrieve full template from S3
                    s3_key = response['Item']['s3_key']
                    s3_response = self.s3.get_object(
                        Bucket=self.s3_bucket,
                        Key=s3_key
                    )
                    template = json.loads(s3_response['Body'].read())
                    return template
            
            # Fallback to built-in templates
            return self._get_builtin_template(template_id)
            
        except ClientError as e:
            logger.error(f"Error retrieving prompt template: {e}")
            return self._get_builtin_template('fallback')
    
    def _get_builtin_template(self, template_id: str) -> Dict[str, Any]:
        """Get built-in prompt templates."""
        templates = {
            'ec2_troubleshooting': {
                'name': 'EC2 Troubleshooting',
                'template': self.base_persona + """

SPECIFIC FOCUS: EC2 Instance Troubleshooting

When helping with EC2 issues:
1. Gather key information: instance ID, region, instance type, OS
2. Check instance status checks (system and instance)
3. Review security groups and network ACLs
4. Verify IAM roles and permissions if applicable
5. Check CloudWatch metrics for performance issues
6. Review system logs and application logs

Common EC2 issues to investigate:
- Instance not reachable (connectivity issues)
- Performance degradation (CPU, memory, network)
- Instance status check failures
- Storage/EBS volume issues
- Instance launch failures

User Query: {query}
Conversation History: {history}

Please provide a structured troubleshooting response.""",
                'parameters': ['query', 'history']
            },
            's3_troubleshooting': {
                'name': 'S3 Troubleshooting',
                'template': self.base_persona + """

SPECIFIC FOCUS: S3 Storage Troubleshooting

When helping with S3 issues:
1. Identify the bucket name and region
2. Check bucket policies and IAM permissions
3. Review CORS configuration if web access is involved
4. Verify versioning and lifecycle policies
5. Check encryption settings
6. Review CloudTrail logs for access attempts

Common S3 issues to investigate:
- Access denied errors (403)
- Missing objects or data
- Performance issues with large files
- Cross-region replication problems
- Bucket policy conflicts

User Query: {query}
Conversation History: {history}

Please provide a structured troubleshooting response.""",
                'parameters': ['query', 'history']
            },
            'lambda_troubleshooting': {
                'name': 'Lambda Troubleshooting',
                'template': self.base_persona + """

SPECIFIC FOCUS: AWS Lambda Troubleshooting

When helping with Lambda issues:
1. Get function name, region, and runtime
2. Check CloudWatch Logs for execution errors
3. Review IAM execution role permissions
4. Verify function timeout and memory settings
5. Check for cold start impacts
6. Review VPC configuration if applicable

Common Lambda issues to investigate:
- Function timeouts
- Memory exceeded errors
- Permission denied errors
- Cold start performance
- VPC connectivity issues
- Concurrent execution limits

User Query: {query}
Conversation History: {history}

Please provide a structured troubleshooting response.""",
                'parameters': ['query', 'history']
            },
            'general_support': {
                'name': 'General AWS Support',
                'template': self.base_persona + """

User Query: {query}
Conversation History: {history}

Please provide helpful and accurate support based on the query above.""",
                'parameters': ['query', 'history']
            },
            'fallback': {
                'name': 'Fallback Template',
                'template': self.base_persona + """

I'm here to help with your AWS question or issue.

User Query: {query}

Please provide your response.""",
                'parameters': ['query']
            }
        }
        
        return templates.get(template_id, templates['general_support'])
    
    def format_prompt(
        self,
        template: Dict[str, Any],
        parameters: Dict[str, str]
    ) -> str:
        """
        Format a prompt template with provided parameters.
        
        Args:
            template: The prompt template
            parameters: Dictionary of parameter values
            
        Returns:
            Formatted prompt string
        """
        prompt_template = template['template']
        
        # Replace parameters in template
        for param in template.get('parameters', []):
            value = parameters.get(param, '')
            prompt_template = prompt_template.replace(f'{{{param}}}', value)
        
        return prompt_template
    
    def invoke_model(
        self,
        prompt: str,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """
        Invoke a Bedrock model with the formatted prompt.
        
        Args:
            prompt: The formatted prompt
            model_id: Bedrock model identifier
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
            top_p: Top-p sampling parameter
            
        Returns:
            Model response
        """
        try:
            # Prepare request body based on model provider
            if "anthropic" in model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            elif "amazon" in model_id:
                body = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": max_tokens,
                        "temperature": temperature,
                        "topP": top_p
                    }
                }
            else:
                raise ValueError(f"Unsupported model: {model_id}")
            
            response = self.bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract content based on model provider
            if "anthropic" in model_id:
                content = response_body['content'][0]['text']
            elif "amazon" in model_id:
                content = response_body['results'][0]['outputText']
            else:
                content = str(response_body)
            
            return {
                'success': True,
                'content': content,
                'model_id': model_id,
                'usage': response_body.get('usage', {})
            }
            
        except ClientError as e:
            logger.error(f"Error invoking model: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def save_prompt_template(
        self,
        template_id: str,
        template: Dict[str, Any],
        version: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a prompt template to S3 and metadata to DynamoDB.
        
        Args:
            template_id: Unique identifier for the template
            template: The prompt template
            version: Version number
            metadata: Optional metadata
            
        Returns:
            Success boolean
        """
        try:
            if not self.s3_bucket or not self.prompt_table:
                logger.warning("S3 bucket or DynamoDB table not configured")
                return False
            
            # Save template to S3
            s3_key = f"prompts/{template_id}/{version}.json"
            self.s3.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json.dumps(template, indent=2),
                ContentType='application/json'
            )
            
            # Save metadata to DynamoDB
            item = {
                'template_id': template_id,
                'version': version,
                's3_key': s3_key,
                'created_at': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
            
            self.prompt_table.put_item(Item=item)
            
            # Update 'latest' pointer
            self.prompt_table.put_item(
                Item={
                    'template_id': template_id,
                    'version': 'latest',
                    's3_key': s3_key,
                    'actual_version': version,
                    'updated_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Saved prompt template {template_id} version {version}")
            return True
            
        except ClientError as e:
            logger.error(f"Error saving prompt template: {e}")
            return False
    
    def list_prompt_templates(self) -> List[Dict[str, Any]]:
        """
        List all available prompt templates.
        
        Returns:
            List of prompt template metadata
        """
        templates = []
        
        try:
            if self.prompt_table:
                response = self.prompt_table.scan()
                templates.extend(response.get('Items', []))
        except ClientError as e:
            logger.error(f"Error listing prompt templates: {e}")
        
        # Add built-in templates
        builtin = [
            {'template_id': 'ec2_troubleshooting', 'name': 'EC2 Troubleshooting', 'source': 'builtin'},
            {'template_id': 's3_troubleshooting', 'name': 'S3 Troubleshooting', 'source': 'builtin'},
            {'template_id': 'lambda_troubleshooting', 'name': 'Lambda Troubleshooting', 'source': 'builtin'},
            {'template_id': 'general_support', 'name': 'General AWS Support', 'source': 'builtin'}
        ]
        templates.extend(builtin)
        
        return templates


