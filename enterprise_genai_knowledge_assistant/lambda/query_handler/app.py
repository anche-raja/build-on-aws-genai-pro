"""
Query Handler Lambda Function
Enhanced with dynamic model selection and comprehensive monitoring
"""

import json
import os
import boto3
import uuid
import time
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

try:
    import tiktoken
except ImportError:
    tiktoken = None

# Import governance handler and quality evaluator
import sys
import os
sys.path.append(os.path.dirname(__file__))
try:
    from governance_handler import GovernanceHandler
except ImportError:
    GovernanceHandler = None
    print("Warning: Governance handler not available")

try:
    from quality_evaluator import QualityEvaluator
except ImportError:
    QualityEvaluator = None
    print("Warning: Quality evaluator not available")

try:
    from feedback_handler import handle_feedback as handle_feedback_func
except ImportError:
    handle_feedback_func = None
    print("Warning: Feedback handler not available")

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')
comprehend = boto3.client('comprehend')
cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')

# Cache table for query responses (DynamoDB)
CACHE_TABLE_NAME = os.environ.get('CONVERSATION_TABLE')  # Reuse conversation table for caching
CACHE_TTL_SECONDS = 3600  # 1 hour cache

# Initialize Governance Handler (Phase 5)
governance = None
if GovernanceHandler:
    try:
        governance = GovernanceHandler(
            audit_table_name=os.environ.get('AUDIT_TRAIL_TABLE', ''),
            audit_bucket=os.environ.get('AUDIT_LOGS_BUCKET', ''),
            sns_topic=os.environ.get('COMPLIANCE_SNS', ''),
            log_group=os.environ.get('GOVERNANCE_LOG_GROUP', '/aws/governance/gka')
        )
    except Exception as e:
        print(f"Warning: Could not initialize governance handler: {str(e)}")

# Initialize Quality Evaluator (Phase 6)
quality_evaluator = None
if QualityEvaluator:
    try:
        quality_evaluator = QualityEvaluator(
            quality_metrics_table=os.environ.get('QUALITY_METRICS_TABLE', ''),
            feedback_table=os.environ.get('USER_FEEDBACK_TABLE', ''),
            log_group=os.environ.get('QUALITY_LOG_GROUP', '/aws/quality/gka')
        )
    except Exception as e:
        print(f"Warning: Could not initialize quality evaluator: {str(e)}")

# Environment variables
METADATA_TABLE = os.environ['METADATA_TABLE']
CONVERSATION_TABLE = os.environ['CONVERSATION_TABLE']
EVALUATION_TABLE = os.environ['EVALUATION_TABLE']
OPENSEARCH_DOMAIN = os.environ['OPENSEARCH_DOMAIN']
OPENSEARCH_SECRET = os.environ.get('OPENSEARCH_SECRET')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize tokenizer for token counting
tokenizer = tiktoken.get_encoding("cl100k_base") if tiktoken else None

# Define model configurations (Updated to current Bedrock model IDs)
models = {
    "simple": {
        "id": "anthropic.claude-3-haiku-20240307-v1:0",
        "max_tokens": 1000,
        "temperature": 0.2,
        "cost_per_1k_input": 0.00025,
        "cost_per_1k_output": 0.00125
    },
    "standard": {
        "id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "max_tokens": 2000,
        "temperature": 0.7,
        "cost_per_1k_input": 0.00800,
        "cost_per_1k_output": 0.02400
    },
    "advanced": {
        "id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "max_tokens": 4000,
        "temperature": 0.7,
        "cost_per_1k_input": 0.00300,
        "cost_per_1k_output": 0.01500
    }
}


def handler(event, context):
    """
    Enhanced query handler with dynamic model selection
    Phase 6: Added feedback handling
    """
    try:
        # Check if this is a feedback request
        path = event.get('path', '')
        if '/feedback' in path:
            if handle_feedback_func and quality_evaluator:
                return handle_feedback_func(event, context, quality_evaluator)
            else:
                return create_response(503, {'error': 'Feedback service not available'})
        
        # Parse request body
        body = json.loads(event['body'])
        query = body.get('query')
        conversation_id = body.get('conversation_id')
        stream = body.get('stream', False)
        
        if not query:
            return create_response(400, {'error': 'Missing query parameter'})
        
        # Generate a new conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        user_id = body.get('user_id', 'anonymous')
        
        # Phase 5: Apply Bedrock Guardrails to input
        if governance and os.environ.get('GUARDRAIL_ID'):
            guardrail_result = governance.check_content_safety(
                query,
                os.environ.get('GUARDRAIL_ID'),
                os.environ.get('GUARDRAIL_VERSION', 'DRAFT')
            )
            
            if not guardrail_result.get('safe'):
                # Content blocked by guardrails
                return create_response(400, {
                    'error': 'Content blocked by safety guardrails',
                    'message': guardrail_result.get('message'),
                    'request_id': request_id
                })
        
        # Phase 5: PII Detection and Redaction
        if governance:
            pii_result = governance.detect_and_redact_pii(query, user_id)
            has_pii = pii_result.get('has_pii', False)
            
            # Use redacted query for processing if PII found
            if has_pii:
                query_for_processing = pii_result.get('redacted_text')
                print(f"PII detected and redacted: {pii_result.get('pii_types')}")
            else:
                query_for_processing = query
        else:
            # Fallback to basic PII detection
            pii_result = detect_pii(query)
            has_pii = len(pii_result.get('Entities', [])) > 0
            query_for_processing = query
        
        # Get conversation history
        conversation_history = get_conversation_history(conversation_id)
        
        # Check cache first (Phase 4: Caching Strategy)
        cached_response = get_cached_response(query, conversation_id)
        if cached_response:
            print(f"Cache hit for query")
            return create_response(200, {
                **cached_response,
                'cached': True,
                'cache_age_seconds': int(time.time() - cached_response.get('cached_at', time.time()))
            })
        
        # Select the appropriate model based on query complexity
        model_tier, complexity_score = select_model_tier(query, conversation_history)
        model_config = models[model_tier]
        
        print(f"Selected model: {model_tier} ({model_config['id']}) - Complexity: {complexity_score}")
        
        # Retrieve relevant chunks using hybrid search (use redacted query)
        relevant_chunks = retrieve_relevant_chunks(query_for_processing, max_results=5, use_hybrid=True)
        
        # Re-rank chunks for better relevance (optional enhancement)
        relevant_chunks = rerank_chunks(query, relevant_chunks)
        
        # Construct prompt with context (use redacted query)
        prompt = construct_prompt(query_for_processing, relevant_chunks, conversation_history)
        
        # Count tokens for cost estimation
        prompt_tokens = count_tokens(prompt)
        
        # Start timing for latency measurement
        start_time = time.time()
        
        # Invoke the model with fallback mechanism (Phase 4: Fallback)
        if stream:
            response = invoke_model_streaming(model_config['id'], prompt, model_config['max_tokens'], model_config['temperature'])
        else:
            response = invoke_model_with_fallback(
                model_tier, prompt, model_config['max_tokens'], 
                model_config['temperature']
            )
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Phase 5: Validate response safety
        if governance and os.environ.get('GUARDRAIL_ID'):
            response_safety = governance.validate_response_safety(
                response,
                os.environ.get('GUARDRAIL_ID'),
                os.environ.get('GUARDRAIL_VERSION', 'DRAFT')
            )
            
            if not response_safety.get('safe'):
                # Response blocked by guardrails
                response = "I apologize, but I cannot provide this response due to content safety policies."
                
                # Log the intervention
                if governance:
                    governance.log_audit_event(
                        event_type='RESPONSE_BLOCKED',
                        user_id=user_id,
                        details={'reason': 'guardrail_intervention'},
                        severity='HIGH'
                    )
        
        # Count response tokens for cost calculation
        response_tokens = count_tokens(response)
        
        # Calculate cost
        cost = calculate_cost(prompt_tokens, response_tokens, model_config)
        
        # Store conversation history
        store_conversation(conversation_id, query, response)
        
        # Log metrics to CloudWatch
        log_metrics(request_id, model_config['id'], prompt_tokens, response_tokens, latency, cost)
        
        # Store evaluation data with complexity score
        store_evaluation_data(
            request_id, query, response, relevant_chunks, 
            model_config['id'], prompt_tokens, response_tokens, 
            latency, cost, model_tier, complexity_score
        )
        
        # Phase 6: Evaluate response quality
        quality_scores = {}
        if quality_evaluator:
            quality_scores = quality_evaluator.evaluate_response_quality(
                query=query,
                response=response,
                relevant_chunks=relevant_chunks,
                metadata={
                    'request_id': request_id,
                    'model_id': model_config['id'],
                    'model_tier': model_tier,
                    'complexity_score': complexity_score
                }
            )
            
            # Log performance metrics
            quality_evaluator.calculate_performance_metrics(
                latency=latency,
                tokens_prompt=prompt_tokens,
                tokens_response=response_tokens,
                cost=cost,
                cached=False
            )
            
            # Log success
            quality_evaluator.log_success_metric()
        
        # Phase 5: Log comprehensive audit trail
        if governance:
            governance.log_query_event(
                request_id=request_id,
                user_id=user_id,
                query=query,
                response=response,
                model_id=model_config['id'],
                has_pii=has_pii,
                guardrail_result={'allowed': True},
                cost=cost,
                latency=latency
            )
        
        # Cache the response for future queries (Phase 4: Caching)
        response_data = {
            'request_id': request_id,
            'conversation_id': conversation_id,
            'response': response,
            'model': model_config['id'],
            'model_tier': model_tier,
            'complexity_score': complexity_score,
            'latency': round(latency, 3),
            'tokens': {
                'prompt': prompt_tokens,
                'response': response_tokens,
                'total': prompt_tokens + response_tokens
            },
            'cost': round(cost, 6),
            'has_pii': has_pii,
            'pii_redacted': has_pii,
            'sources': [{'document_id': c['document_id'], 'score': c['score']} for c in relevant_chunks],
            'cached': False,
            'governance': {
                'guardrails_applied': bool(os.environ.get('GUARDRAIL_ID')),
                'pii_detected': has_pii,
                'audit_logged': governance is not None
            },
            'quality_scores': quality_scores if quality_scores else None
        }
        
        cache_response(query, conversation_id, response_data)
        
        return create_response(200, response_data)
    
    except Exception as e:
        print(f"Error handling query: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Phase 6: Log error metrics
        if quality_evaluator:
            quality_evaluator.log_error_metric(
                error_type=type(e).__name__,
                error_message=str(e)
            )
        
        return create_response(500, {
            'error': f'Internal server error: {str(e)}'
        })


def detect_pii(text):
    """Detect PII in text using AWS Comprehend"""
    try:
        response = comprehend.detect_pii_entities(
            Text=text[:5000],  # Comprehend limit
            LanguageCode='en'
        )
        return response
    except Exception as e:
        print(f"Error detecting PII: {str(e)}")
        return {'Entities': []}


def get_conversation_history(conversation_id):
    """Retrieve conversation history from DynamoDB"""
    try:
        table = dynamodb.Table(CONVERSATION_TABLE)
        response = table.query(
            KeyConditionExpression='conversation_id = :cid',
            ExpressionAttributeValues={
                ':cid': conversation_id
            },
            ScanIndexForward=True,
            Limit=10  # Get the last 10 exchanges
        )
        
        return response.get('Items', [])
    except Exception as e:
        print(f"Error getting conversation history: {str(e)}")
        return []


def analyze_query_complexity(query, conversation_history):
    """
    Enhanced query complexity analysis with scoring system
    Returns complexity score (0-100) and factors
    """
    complexity_score = 0
    factors = []
    
    # Factor 1: Query length (0-20 points)
    query_length = len(query.split())
    if query_length < 5:
        complexity_score += 5
        factors.append("very_short")
    elif query_length < 10:
        complexity_score += 10
        factors.append("short")
    elif query_length < 20:
        complexity_score += 15
        factors.append("medium")
    else:
        complexity_score += 20
        factors.append("long")
    
    # Factor 2: Conversation depth (0-15 points)
    conversation_length = len(conversation_history)
    complexity_score += min(conversation_length * 3, 15)
    if conversation_length > 5:
        factors.append("deep_conversation")
    
    # Factor 3: Complex indicators (0-25 points)
    complex_indicators = {
        "comparison": ["compare", "difference between", "versus", "vs"],
        "analysis": ["analyze", "evaluation", "assessment", "critique"],
        "explanation": ["explain", "why", "how does", "what causes"],
        "reasoning": ["pros and cons", "advantages", "disadvantages", "trade-offs"],
        "multi-step": ["first", "then", "finally", "step by step"]
    }
    
    for category, keywords in complex_indicators.items():
        if any(keyword in query.lower() for keyword in keywords):
            complexity_score += 5
            factors.append(f"complex_{category}")
    
    # Factor 4: Technical terminology (0-20 points)
    technical_domains = {
        "architecture": ["architecture", "design pattern", "infrastructure", "topology"],
        "security": ["security", "authentication", "encryption", "vulnerability"],
        "performance": ["optimization", "performance", "latency", "throughput"],
        "implementation": ["implementation", "configuration", "deployment", "integration"]
    }
    
    for domain, terms in technical_domains.items():
        if any(term in query.lower() for term in terms):
            complexity_score += 5
            factors.append(f"technical_{domain}")
    
    # Factor 5: Question type (0-20 points)
    question_types = {
        "what": 5,
        "how": 10,
        "why": 15,
        "when": 5,
        "where": 5,
        "which": 10
    }
    
    for q_type, score in question_types.items():
        if query.lower().startswith(q_type):
            complexity_score += score
            factors.append(f"question_{q_type}")
            break
    
    return min(complexity_score, 100), factors


def select_model_tier(query, conversation_history):
    """
    Enhanced model selection with complexity scoring
    """
    complexity_score, factors = analyze_query_complexity(query, conversation_history)
    
    print(f"Query complexity score: {complexity_score}, factors: {factors}")
    
    # Select model based on complexity score
    if complexity_score >= 60:
        return "advanced", complexity_score
    elif complexity_score >= 30:
        return "standard", complexity_score
    else:
        return "simple", complexity_score


def retrieve_relevant_chunks(query, max_results=5, use_hybrid=True):
    """
    Retrieve relevant document chunks using hybrid search (vector + keyword)
    
    Args:
        query: User query text
        max_results: Number of results to return
        use_hybrid: If True, uses hybrid search; if False, uses pure vector search
    """
    try:
        # Generate query embedding for vector search
        embedding = generate_embedding(query)
        
        # Get OpenSearch client
        client = get_opensearch_client()
        
        if use_hybrid:
            # Hybrid search: Combine vector similarity + keyword matching
            search_body = {
                'size': max_results,
                'query': {
                    'bool': {
                        'should': [
                            # Vector similarity search (70% weight)
                            {
                                'script_score': {
                                    'query': {'match_all': {}},
                                    'script': {
                                        'source': "knn_score",
                                        'lang': 'knn',
                                        'params': {
                                            'field': 'embedding',
                                            'query_value': embedding,
                                            'space_type': 'cosinesimil'
                                        }
                                    },
                                    'boost': 0.7
                                }
                            },
                            # Keyword search (30% weight)
                            {
                                'multi_match': {
                                    'query': query,
                                    'fields': ['text^2', 'document_id'],  # Boost text field
                                    'type': 'best_fields',
                                    'boost': 0.3
                                }
                            }
                        ],
                        'minimum_should_match': 1
                    }
                },
                '_source': ['document_id', 'chunk_id', 'text', 'tokens']
            }
        else:
            # Pure vector search (original implementation)
            search_body = {
                'size': max_results,
                'query': {
                    'knn': {
                        'embedding': {
                            'vector': embedding,
                            'k': max_results
                        }
                    }
                },
                '_source': ['document_id', 'chunk_id', 'text', 'tokens']
            }
        
        # Execute search
        response = client.search(
            index='document-chunks',
            body=search_body
        )
        
        # Parse results
        chunks = []
        for hit in response['hits']['hits']:
            chunks.append({
                'text': hit['_source']['text'],
                'document_id': hit['_source']['document_id'],
                'chunk_id': hit['_source']['chunk_id'],
                'score': float(hit['_score'])
            })
        
        print(f"Retrieved {len(chunks)} chunks using {'hybrid' if use_hybrid else 'vector'} search")
        return chunks
    
    except Exception as e:
        print(f"Error retrieving relevant chunks: {str(e)}")
        # Return empty list if retrieval fails
        return []


def generate_embedding(text):
    """Generate embedding for query text"""
    try:
        response = bedrock_runtime.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text})
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embedding']
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return [0.0] * 1536


def construct_prompt(query, relevant_chunks, conversation_history):
    """Construct prompt with context and conversation history"""
    # Start with system instructions
    prompt = """You are a helpful, accurate, and concise knowledge assistant. 
Answer questions based only on the provided context. 
If you don't have enough information to answer the question, say "I don't have enough information to answer this question."
Do not make up information or use knowledge outside of the provided context.

Context information:
"""
    
    # Add relevant chunks as context
    if relevant_chunks:
        for i, chunk in enumerate(relevant_chunks):
            prompt += f"\n--- Document {i+1} (Relevance: {chunk['score']:.2f}) ---\n{chunk['text']}\n"
    else:
        prompt += "\nNo relevant context found.\n"
    
    # Add conversation history
    if conversation_history:
        prompt += "\nPrevious conversation:\n"
        for exchange in conversation_history[-6:]:  # Last 3 exchanges (6 messages)
            prompt += f"Human: {exchange.get('query', '')}\n"
            prompt += f"Assistant: {exchange.get('response', '')}\n"
    
    # Add the current query
    prompt += f"\nHuman: {query}\n\nAssistant:"
    
    return prompt


def invoke_model(model_id, prompt, max_tokens, temperature):
    """Invoke Bedrock model for response generation"""
    try:
        # Prepare request body for Claude models
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    except Exception as e:
        print(f"Error invoking model {model_id}: {str(e)}")
        raise  # Re-raise for fallback handling


def invoke_model_with_fallback(model_tier, prompt, max_tokens, temperature):
    """
    Phase 4: Fallback Mechanism
    Try primary model, fall back to lower tiers if it fails
    """
    # Define fallback chain
    fallback_chain = {
        "advanced": ["advanced", "standard", "simple"],
        "standard": ["standard", "simple"],
        "simple": ["simple"]
    }
    
    tiers_to_try = fallback_chain.get(model_tier, ["simple"])
    
    for tier in tiers_to_try:
        try:
            model_config = models[tier]
            print(f"Attempting model: {tier} ({model_config['id']})")
            
            response = invoke_model(
                model_config['id'],
                prompt,
                model_config['max_tokens'],
                temperature
            )
            
            if tier != model_tier:
                print(f"Fallback successful: Used {tier} instead of {model_tier}")
            
            return response
        
        except Exception as e:
            print(f"Model {tier} failed: {str(e)}")
            if tier == tiers_to_try[-1]:
                # Last option failed
                return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
            # Try next model in fallback chain
            continue


def invoke_model_streaming(model_id, prompt, max_tokens, temperature):
    """
    Invoke model with streaming (placeholder)
    In production, implement with invoke_model_with_response_stream
    """
    # For now, use non-streaming version
    return invoke_model(model_id, prompt, max_tokens, temperature)


def count_tokens(text):
    """Count tokens in text"""
    if tokenizer:
        return len(tokenizer.encode(text))
    else:
        # Fallback estimation
        return len(text) // 4


def calculate_cost(prompt_tokens, response_tokens, model_config):
    """Calculate cost based on token usage"""
    prompt_cost = (prompt_tokens / 1000) * model_config['cost_per_1k_input']
    response_cost = (response_tokens / 1000) * model_config['cost_per_1k_output']
    return prompt_cost + response_cost


def store_conversation(conversation_id, query, response):
    """Store conversation exchange in DynamoDB"""
    try:
        table = dynamodb.Table(CONVERSATION_TABLE)
        timestamp = int(datetime.utcnow().timestamp())
        ttl = timestamp + (30 * 24 * 60 * 60)  # 30 days
        
        table.put_item(Item={
            'conversation_id': conversation_id,
            'timestamp': timestamp,
            'query': query,
            'response': response,
            'ttl': ttl
        })
    except Exception as e:
        print(f"Error storing conversation: {str(e)}")


def log_metrics(request_id, model_id, prompt_tokens, response_tokens, latency, cost):
    """Log metrics to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='GenAI/KnowledgeAssistant',
            MetricData=[
                {
                    'MetricName': 'QueryLatency',
                    'Value': latency,
                    'Unit': 'Seconds',
                    'Dimensions': [
                        {'Name': 'ModelId', 'Value': model_id}
                    ]
                },
                {
                    'MetricName': 'PromptTokens',
                    'Value': prompt_tokens,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'ModelId', 'Value': model_id}
                    ]
                },
                {
                    'MetricName': 'ResponseTokens',
                    'Value': response_tokens,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'ModelId', 'Value': model_id}
                    ]
                },
                {
                    'MetricName': 'QueryCost',
                    'Value': cost,
                    'Unit': 'None',
                    'Dimensions': [
                        {'Name': 'ModelId', 'Value': model_id}
                    ]
                }
            ]
        )
    except Exception as e:
        print(f"Error logging metrics: {str(e)}")


def get_cached_response(query, conversation_id):
    """
    Phase 4: Caching Strategy
    Check if we have a cached response for this query
    """
    try:
        import hashlib
        
        # Create cache key from query
        cache_key = hashlib.md5(query.lower().strip().encode()).hexdigest()
        
        table = dynamodb.Table(CONVERSATION_TABLE)
        
        # Query for cached response
        response = table.get_item(
            Key={
                'conversation_id': f"cache_{cache_key}",
                'timestamp': 0  # Use 0 for cache entries
            }
        )
        
        if 'Item' in response:
            cached_item = response['Item']
            cached_at = cached_item.get('cached_at', 0)
            
            # Check if cache is still valid
            if time.time() - cached_at < CACHE_TTL_SECONDS:
                print(f"Cache hit: {cache_key}")
                return json.loads(cached_item.get('response_data', '{}'))
            else:
                print(f"Cache expired: {cache_key}")
                return None
        
        return None
    
    except Exception as e:
        print(f"Error checking cache: {str(e)}")
        return None


def cache_response(query, conversation_id, response_data):
    """
    Phase 4: Caching Strategy
    Cache the response for future identical queries
    """
    try:
        import hashlib
        
        # Create cache key from query
        cache_key = hashlib.md5(query.lower().strip().encode()).hexdigest()
        
        table = dynamodb.Table(CONVERSATION_TABLE)
        
        # Store in cache
        table.put_item(Item={
            'conversation_id': f"cache_{cache_key}",
            'timestamp': 0,  # Use 0 for cache entries
            'query': query,
            'response_data': json.dumps(response_data),
            'cached_at': int(time.time()),
            'ttl': int(time.time()) + CACHE_TTL_SECONDS
        })
        
        print(f"Response cached: {cache_key}")
    
    except Exception as e:
        print(f"Error caching response: {str(e)}")


def store_evaluation_data(request_id, query, response, relevant_chunks, model_id, 
                         prompt_tokens, response_tokens, latency, cost, model_tier, complexity_score):
    """Store evaluation data for later analysis with complexity score"""
    try:
        table = dynamodb.Table(EVALUATION_TABLE)
        
        table.put_item(Item={
            'request_id': request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'query': query,
            'response': response,
            'model_id': model_id,
            'model_tier': model_tier,
            'complexity_score': int(complexity_score),
            'prompt_tokens': prompt_tokens,
            'response_tokens': response_tokens,
            'total_tokens': prompt_tokens + response_tokens,
            'latency': float(latency),
            'cost': float(cost),
            'chunks_retrieved': len(relevant_chunks),
            'avg_chunk_score': sum(c['score'] for c in relevant_chunks) / len(relevant_chunks) if relevant_chunks else 0
        })
    except Exception as e:
        print(f"Error storing evaluation data: {str(e)}")


def rerank_chunks(query, chunks, top_k=5):
    """
    Re-rank retrieved chunks for better relevance (optional enhancement)
    
    Uses simple heuristics:
    - Penalize very short chunks
    - Boost chunks with query keywords
    - Consider chunk position/score
    """
    if not chunks:
        return chunks
    
    query_terms = set(query.lower().split())
    
    for chunk in chunks:
        # Start with original score
        adjusted_score = chunk['score']
        
        # Penalize very short chunks (< 100 tokens)
        chunk_length = len(chunk['text'].split())
        if chunk_length < 100:
            adjusted_score *= 0.8
        
        # Boost if query keywords appear in chunk
        chunk_terms = set(chunk['text'].lower().split())
        keyword_overlap = len(query_terms & chunk_terms) / len(query_terms) if query_terms else 0
        adjusted_score *= (1 + keyword_overlap * 0.3)
        
        chunk['adjusted_score'] = adjusted_score
    
    # Sort by adjusted score
    chunks = sorted(chunks, key=lambda x: x.get('adjusted_score', x['score']), reverse=True)
    
    return chunks[:top_k]


def get_opensearch_client():
    """Create OpenSearch client with AWS authentication"""
    credentials = boto3.Session().get_credentials()
    
    auth = AWSRequestsAuth(
        aws_access_key=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_token=credentials.token,
        aws_host=OPENSEARCH_DOMAIN,
        aws_region=AWS_REGION,
        aws_service='es'
    )
    
    return OpenSearch(
        hosts=[{'host': OPENSEARCH_DOMAIN, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )


def create_response(status_code, body):
    """Create API Gateway response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS,POST,PUT,DELETE',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }
