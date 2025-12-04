"""
Phase 6: RAG Application
Complete Retrieval-Augmented Generation application
"""

import boto3
import json
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGApplication:
    """Complete RAG application combining retrieval and generation"""
    
    def __init__(
        self,
        bedrock_manager,
        opensearch_manager=None,
        metadata_manager=None,
        region: str = 'us-east-1'
    ):
        """
        Initialize RAG application
        
        Args:
            bedrock_manager: BedrockManager instance
            opensearch_manager: Optional OpenSearchManager instance
            metadata_manager: Optional MetadataManager instance
            region: AWS region
        """
        self.bedrock = bedrock_manager
        self.opensearch = opensearch_manager
        self.metadata = metadata_manager
        self.region = region
        
        # Query cache for frequent queries
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def retrieve_context(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        index_name: Optional[str] = None,
        num_results: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve relevant context for a query
        
        Args:
            query: User query
            knowledge_base_id: Bedrock Knowledge Base ID (if using Bedrock)
            index_name: OpenSearch index name (if using OpenSearch)
            num_results: Number of results to retrieve
            filters: Optional metadata filters
            
        Returns:
            List of relevant document chunks
        """
        try:
            results = []
            
            # Try Knowledge Base first if provided
            if knowledge_base_id:
                kb_results = self.bedrock.retrieve_from_knowledge_base(
                    knowledge_base_id=knowledge_base_id,
                    query=query,
                    num_results=num_results
                )
                
                for result in kb_results:
                    results.append({
                        'text': result['content']['text'],
                        'score': result['score'],
                        'metadata': result.get('metadata', {}),
                        'source': 'knowledge_base'
                    })
            
            # Use OpenSearch if provided
            elif index_name and self.opensearch:
                # Generate embedding for query
                query_embedding = self.bedrock.generate_embedding(query)
                
                # Search OpenSearch
                search_results = self.opensearch.vector_search(
                    index_name=index_name,
                    query_vector=query_embedding,
                    k=num_results,
                    filters=filters
                )
                
                for hit in search_results['hits']['hits']:
                    results.append({
                        'text': hit['_source'].get('content', ''),
                        'score': hit['_score'],
                        'metadata': hit['_source'].get('metadata', {}),
                        'source': 'opensearch',
                        'document_id': hit['_source'].get('document_id', '')
                    })
            
            logger.info(f"Retrieved {len(results)} context chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            raise
    
    def optimize_context_window(
        self,
        context_chunks: List[Dict],
        max_tokens: int = 3000
    ) -> str:
        """
        Optimize context to fit within token limit
        
        Args:
            context_chunks: List of context chunks
            max_tokens: Maximum tokens for context
            
        Returns:
            Optimized context string
        """
        # Simple approximation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        # Sort by relevance score
        sorted_chunks = sorted(context_chunks, key=lambda x: x.get('score', 0), reverse=True)
        
        context = ""
        for chunk in sorted_chunks:
            chunk_text = chunk['text']
            if len(context) + len(chunk_text) <= max_chars:
                context += f"\n\n{chunk_text}"
            else:
                break
        
        return context.strip()
    
    def build_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Build prompt for the foundation model
        
        Args:
            query: User query
            context: Retrieved context
            system_prompt: Optional system prompt
            
        Returns:
            Complete prompt
        """
        if system_prompt is None:
            system_prompt = """You are a helpful AI assistant. Answer questions based on the provided context.
If the context doesn't contain enough information to answer the question, say so.
Always cite the relevant parts of the context in your answer."""
        
        prompt = f"""{system_prompt}

Context:
{context}

Question: {query}

Answer:"""
        
        return prompt
    
    def generate_response(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        index_name: Optional[str] = None,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        num_context_chunks: int = 5,
        filters: Optional[Dict] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> Dict:
        """
        Generate RAG response for a query
        
        Args:
            query: User query
            knowledge_base_id: Bedrock Knowledge Base ID
            index_name: OpenSearch index name
            model_id: Foundation model ID
            num_context_chunks: Number of context chunks to retrieve
            filters: Optional metadata filters
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Dictionary containing response and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Check cache
            cache_key = f"{query}:{knowledge_base_id}:{index_name}"
            if cache_key in self.query_cache:
                cached_result = self.query_cache[cache_key]
                if (datetime.utcnow() - cached_result['timestamp']).seconds < self.cache_ttl:
                    logger.info("Returning cached response")
                    return cached_result['response']
            
            # Step 1: Retrieve relevant context
            context_chunks = self.retrieve_context(
                query=query,
                knowledge_base_id=knowledge_base_id,
                index_name=index_name,
                num_results=num_context_chunks,
                filters=filters
            )
            
            if not context_chunks:
                return {
                    'answer': "I couldn't find relevant information to answer your question.",
                    'sources': [],
                    'metadata': {
                        'query': query,
                        'num_sources': 0,
                        'processing_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000
                    }
                }
            
            # Step 2: Optimize context window
            context = self.optimize_context_window(context_chunks, max_tokens=3000)
            
            # Step 3: Build prompt
            prompt = self.build_prompt(query, context)
            
            # Step 4: Generate response
            answer = self.bedrock.invoke_foundation_model(
                prompt=prompt,
                model_id=model_id,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Step 5: Prepare response with metadata
            response = {
                'answer': answer,
                'sources': [
                    {
                        'text': chunk['text'][:200] + '...',  # Truncate for brevity
                        'score': chunk['score'],
                        'metadata': chunk.get('metadata', {})
                    }
                    for chunk in context_chunks
                ],
                'metadata': {
                    'query': query,
                    'model_id': model_id,
                    'num_sources': len(context_chunks),
                    'processing_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            # Cache the response
            self.query_cache[cache_key] = {
                'response': response,
                'timestamp': datetime.utcnow()
            }
            
            logger.info(f"Generated response in {response['metadata']['processing_time_ms']:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def conversation_response(
        self,
        query: str,
        conversation_history: List[Dict],
        knowledge_base_id: Optional[str] = None,
        index_name: Optional[str] = None,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    ) -> Dict:
        """
        Generate response with conversation context
        
        Args:
            query: Current user query
            conversation_history: List of previous messages
            knowledge_base_id: Bedrock Knowledge Base ID
            index_name: OpenSearch index name
            model_id: Foundation model ID
            
        Returns:
            Response with conversation awareness
        """
        # Enhance query with conversation context
        if conversation_history:
            recent_context = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation_history[-3:]  # Last 3 messages
            ])
            enhanced_query = f"Conversation context:\n{recent_context}\n\nCurrent question: {query}"
        else:
            enhanced_query = query
        
        # Generate response
        return self.generate_response(
            query=enhanced_query,
            knowledge_base_id=knowledge_base_id,
            index_name=index_name,
            model_id=model_id
        )
    
    def batch_query(
        self,
        queries: List[str],
        knowledge_base_id: Optional[str] = None,
        index_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Process multiple queries in batch
        
        Args:
            queries: List of queries
            knowledge_base_id: Bedrock Knowledge Base ID
            index_name: OpenSearch index name
            
        Returns:
            List of responses
        """
        responses = []
        
        for query in queries:
            try:
                response = self.generate_response(
                    query=query,
                    knowledge_base_id=knowledge_base_id,
                    index_name=index_name
                )
                responses.append(response)
            except Exception as e:
                logger.error(f"Error processing query '{query}': {str(e)}")
                responses.append({
                    'answer': f"Error processing query: {str(e)}",
                    'sources': [],
                    'metadata': {'query': query, 'error': str(e)}
                })
        
        return responses
    
    def collect_feedback(
        self,
        query: str,
        response: Dict,
        rating: int,
        comment: Optional[str] = None
    ) -> Dict:
        """
        Collect user feedback on responses
        
        Args:
            query: Original query
            response: Generated response
            rating: Rating (1-5)
            comment: Optional comment
            
        Returns:
            Feedback record
        """
        feedback = {
            'query': query,
            'response_id': response['metadata'].get('timestamp', ''),
            'rating': rating,
            'comment': comment,
            'timestamp': datetime.utcnow().isoformat(),
            'num_sources': response['metadata'].get('num_sources', 0)
        }
        
        logger.info(f"Collected feedback: rating={rating}")
        
        # In production, store this in DynamoDB or similar
        return feedback


if __name__ == "__main__":
    # Example usage
    from bedrock_manager import BedrockManager
    
    bedrock = BedrockManager()
    rag_app = RAGApplication(bedrock_manager=bedrock)
    
    print("RAG Application initialized")
    
    # Example query
    # response = rag_app.generate_response(
    #     query="What is Amazon Bedrock?",
    #     knowledge_base_id="your-kb-id"
    # )
    # print(json.dumps(response, indent=2))

