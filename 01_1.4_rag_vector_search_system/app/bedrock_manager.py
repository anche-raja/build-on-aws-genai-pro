"""
Phase 1: Amazon Bedrock Knowledge Base and Foundation Model Manager
Handles setup and management of Bedrock resources
"""

import boto3
import json
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BedrockManager:
    """Manages Amazon Bedrock Knowledge Bases and Foundation Models"""
    
    def __init__(self, region_name: str = 'us-east-1'):
        self.bedrock = boto3.client('bedrock', region_name=region_name)
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region_name)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region_name)
        self.region = region_name
    
    def create_knowledge_base(
        self,
        name: str,
        description: str,
        role_arn: str,
        embedding_model: str = "amazon.titan-embed-text-v1"
    ) -> Dict:
        """
        Create a new Amazon Bedrock Knowledge Base
        
        Args:
            name: Knowledge base name
            description: Description of the knowledge base
            role_arn: IAM role ARN with appropriate permissions
            embedding_model: Embedding model to use
            
        Returns:
            Dict containing knowledge base details
        """
        try:
            response = self.bedrock_agent.create_knowledge_base(
                name=name,
                description=description,
                roleArn=role_arn,
                knowledgeBaseConfiguration={
                    'type': 'VECTOR',
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': f"arn:aws:bedrock:{self.region}::foundation-model/{embedding_model}"
                    }
                },
                storageConfiguration={
                    'type': 'OPENSEARCH_SERVERLESS',
                    'opensearchServerlessConfiguration': {
                        'collectionArn': '',  # To be populated
                        'vectorIndexName': 'bedrock-knowledge-base-default-index',
                        'fieldMapping': {
                            'vectorField': 'embedding',
                            'textField': 'text',
                            'metadataField': 'metadata'
                        }
                    }
                }
            )
            
            knowledge_base_id = response['knowledgeBase']['knowledgeBaseId']
            logger.info(f"Created Knowledge Base with ID: {knowledge_base_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")
            raise
    
    def create_data_source(
        self,
        knowledge_base_id: str,
        name: str,
        bucket_arn: str,
        inclusion_prefixes: List[str] = None
    ) -> Dict:
        """
        Create a data source for the Knowledge Base
        
        Args:
            knowledge_base_id: ID of the knowledge base
            name: Data source name
            bucket_arn: S3 bucket ARN containing documents
            inclusion_prefixes: List of S3 prefixes to include
            
        Returns:
            Dict containing data source details
        """
        try:
            config = {
                'type': 'S3',
                's3Configuration': {
                    'bucketArn': bucket_arn
                }
            }
            
            if inclusion_prefixes:
                config['s3Configuration']['inclusionPrefixes'] = inclusion_prefixes
            
            response = self.bedrock_agent.create_data_source(
                knowledgeBaseId=knowledge_base_id,
                name=name,
                description=f"Data source for {name}",
                dataSourceConfiguration=config,
                vectorIngestionConfiguration={
                    'chunkingConfiguration': {
                        'chunkingStrategy': 'FIXED_SIZE',
                        'fixedSizeChunkingConfiguration': {
                            'maxTokens': 300,
                            'overlapPercentage': 10
                        }
                    }
                }
            )
            
            data_source_id = response['dataSource']['dataSourceId']
            logger.info(f"Created Data Source with ID: {data_source_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error creating data source: {str(e)}")
            raise
    
    def start_ingestion_job(self, knowledge_base_id: str, data_source_id: str) -> Dict:
        """
        Start an ingestion job for a data source
        
        Args:
            knowledge_base_id: ID of the knowledge base
            data_source_id: ID of the data source
            
        Returns:
            Dict containing ingestion job details
        """
        try:
            response = self.bedrock_agent.start_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id
            )
            
            logger.info(f"Started ingestion job: {response['ingestionJob']['ingestionJobId']}")
            return response
            
        except Exception as e:
            logger.error(f"Error starting ingestion job: {str(e)}")
            raise
    
    def generate_embedding(self, text: str, model_id: str = "amazon.titan-embed-text-v1") -> List[float]:
        """
        Generate embedding for given text using Bedrock
        
        Args:
            text: Text to embed
            model_id: Embedding model ID
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"inputText": text})
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def invoke_foundation_model(
        self,
        prompt: str,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """
        Invoke a foundation model for text generation
        
        Args:
            prompt: Input prompt
            model_id: Foundation model ID
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text response
        """
        try:
            # Format for Claude models
            if "anthropic.claude" in model_id:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            else:
                # Generic format
                body = json.dumps({
                    "prompt": prompt,
                    "maxTokens": max_tokens,
                    "temperature": temperature
                })
            
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract text based on model
            if "anthropic.claude" in model_id:
                return response_body['content'][0]['text']
            else:
                return response_body.get('completion', response_body.get('results', [{}])[0].get('outputText', ''))
                
        except Exception as e:
            logger.error(f"Error invoking foundation model: {str(e)}")
            raise
    
    def retrieve_from_knowledge_base(
        self,
        knowledge_base_id: str,
        query: str,
        num_results: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant documents from Knowledge Base
        
        Args:
            knowledge_base_id: ID of the knowledge base
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of relevant document chunks
        """
        try:
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': num_results
                    }
                }
            )
            
            return response['retrievalResults']
            
        except Exception as e:
            logger.error(f"Error retrieving from knowledge base: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    manager = BedrockManager()
    
    # Generate embedding example
    text = "Amazon Bedrock is a fully managed service for foundation models"
    embedding = manager.generate_embedding(text)
    print(f"Generated embedding with dimension: {len(embedding)}")
    
    # Invoke model example
    prompt = "What is Amazon Bedrock?"
    response = manager.invoke_foundation_model(prompt)
    print(f"Model response: {response}")

