"""
Quality Evaluation Module
Phase 6: Monitoring and Evaluation
"""

import json
import boto3
import uuid
from datetime import datetime
import hashlib
import re

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')
logs_client = boto3.client('logs')


class QualityEvaluator:
    """Handles quality evaluation, metrics collection, and user feedback"""
    
    def __init__(self, quality_metrics_table, feedback_table, log_group):
        self.quality_metrics_table = dynamodb.Table(quality_metrics_table)
        self.feedback_table = dynamodb.Table(feedback_table)
        self.log_group = log_group
    
    def evaluate_response_quality(self, query, response, relevant_chunks, metadata=None):
        """
        Phase 6: Comprehensive Response Quality Evaluation
        Evaluates response across multiple dimensions
        """
        try:
            scores = {}
            
            # 1. Relevance Score: How well does response match query intent?
            scores['relevance'] = self._calculate_relevance_score(query, response, relevant_chunks)
            
            # 2. Coherence Score: Is the response well-structured and logical?
            scores['coherence'] = self._calculate_coherence_score(response)
            
            # 3. Completeness Score: Does response fully address the query?
            scores['completeness'] = self._calculate_completeness_score(query, response)
            
            # 4. Accuracy Score: Based on source document relevance
            scores['accuracy'] = self._calculate_accuracy_score(relevant_chunks)
            
            # 5. Conciseness Score: Is the response appropriately concise?
            scores['conciseness'] = self._calculate_conciseness_score(response)
            
            # 6. Groundedness Score: Is response grounded in provided context?
            scores['groundedness'] = self._calculate_groundedness_score(response, relevant_chunks)
            
            # Overall quality score (weighted average)
            overall_score = self._calculate_overall_score(scores)
            scores['overall'] = overall_score
            
            # Store quality metrics
            self._store_quality_metrics(scores, metadata)
            
            # Send CloudWatch metrics
            self._send_quality_metrics(scores)
            
            return scores
        
        except Exception as e:
            print(f"Error evaluating quality: {str(e)}")
            return {
                'relevance': 0.0,
                'coherence': 0.0,
                'completeness': 0.0,
                'accuracy': 0.0,
                'conciseness': 0.0,
                'groundedness': 0.0,
                'overall': 0.0,
                'error': str(e)
            }
    
    def _calculate_relevance_score(self, query, response, chunks):
        """Calculate relevance based on keyword overlap and semantic similarity"""
        try:
            # Extract keywords from query
            query_keywords = set(re.findall(r'\w+', query.lower()))
            query_keywords = {w for w in query_keywords if len(w) > 3}
            
            # Extract keywords from response
            response_keywords = set(re.findall(r'\w+', response.lower()))
            
            # Calculate overlap
            if not query_keywords:
                return 0.5
            
            overlap = len(query_keywords & response_keywords) / len(query_keywords)
            
            # Factor in chunk scores
            if chunks:
                avg_chunk_score = sum(c.get('score', 0) for c in chunks) / len(chunks)
                score = (overlap * 0.6) + (avg_chunk_score * 0.4)
            else:
                score = overlap
            
            return min(max(score, 0.0), 1.0)
        
        except Exception as e:
            print(f"Error calculating relevance: {str(e)}")
            return 0.5
    
    def _calculate_coherence_score(self, response):
        """Calculate coherence based on structure and flow"""
        try:
            # Check for proper sentence structure
            sentences = response.split('.')
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return 0.0
            
            score = 0.0
            
            # Check average sentence length (too short or too long reduces score)
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_length <= 25:
                score += 0.3
            elif 5 <= avg_length <= 35:
                score += 0.15
            
            # Check for transition words/phrases
            transitions = ['however', 'therefore', 'additionally', 'furthermore', 
                          'moreover', 'consequently', 'thus', 'hence', 'for example']
            has_transitions = any(t in response.lower() for t in transitions)
            if has_transitions:
                score += 0.2
            
            # Check for logical flow (not too repetitive)
            unique_words = len(set(response.lower().split()))
            total_words = len(response.split())
            if total_words > 0:
                uniqueness = unique_words / total_words
                if uniqueness > 0.5:
                    score += 0.3
                elif uniqueness > 0.3:
                    score += 0.15
            
            # Check for proper capitalization and punctuation
            if response[0].isupper() and response.endswith(('.', '!', '?')):
                score += 0.2
            
            return min(score, 1.0)
        
        except Exception as e:
            print(f"Error calculating coherence: {str(e)}")
            return 0.5
    
    def _calculate_completeness_score(self, query, response):
        """Calculate completeness based on question type and response"""
        try:
            score = 0.0
            
            # Check if query is a question
            is_question = '?' in query
            
            # Check response length (very short responses are likely incomplete)
            word_count = len(response.split())
            if word_count > 50:
                score += 0.4
            elif word_count > 20:
                score += 0.3
            elif word_count > 10:
                score += 0.2
            else:
                score += 0.1
            
            # Check for question words and if they're addressed
            question_words = {
                'what': ['is', 'are', 'definition', 'means'],
                'how': ['by', 'through', 'steps', 'process'],
                'why': ['because', 'due to', 'reason', 'since'],
                'when': ['time', 'date', 'during', 'after', 'before'],
                'where': ['location', 'place', 'at', 'in'],
                'who': ['person', 'people', 'individual', 'organization']
            }
            
            query_lower = query.lower()
            response_lower = response.lower()
            
            for qword, indicators in question_words.items():
                if qword in query_lower:
                    if any(ind in response_lower for ind in indicators):
                        score += 0.3
                        break
            
            # Check for examples (indicates thoroughness)
            has_examples = any(phrase in response_lower for phrase in 
                             ['for example', 'for instance', 'such as', 'like'])
            if has_examples:
                score += 0.2
            
            # Check if response acknowledges uncertainty appropriately
            if "I don't" in response or "I cannot" in response or "I'm not sure" in response:
                # This is actually good - honest about limitations
                score += 0.1
            
            return min(score, 1.0)
        
        except Exception as e:
            print(f"Error calculating completeness: {str(e)}")
            return 0.5
    
    def _calculate_accuracy_score(self, chunks):
        """Calculate accuracy based on source relevance"""
        try:
            if not chunks:
                return 0.0
            
            # Average of chunk scores
            avg_score = sum(c.get('score', 0) for c in chunks) / len(chunks)
            
            # Bonus for having multiple high-quality sources
            high_quality_chunks = sum(1 for c in chunks if c.get('score', 0) > 0.8)
            if high_quality_chunks >= 3:
                avg_score = min(avg_score + 0.1, 1.0)
            
            return avg_score
        
        except Exception as e:
            print(f"Error calculating accuracy: {str(e)}")
            return 0.5
    
    def _calculate_conciseness_score(self, response):
        """Calculate conciseness (not too long, not too short)"""
        try:
            word_count = len(response.split())
            
            # Optimal range is 50-200 words
            if 50 <= word_count <= 200:
                return 1.0
            elif 30 <= word_count < 50:
                return 0.8
            elif 200 < word_count <= 300:
                return 0.8
            elif 20 <= word_count < 30:
                return 0.6
            elif 300 < word_count <= 500:
                return 0.6
            elif word_count < 20:
                return 0.3
            else:  # > 500 words
                return 0.4
        
        except Exception as e:
            print(f"Error calculating conciseness: {str(e)}")
            return 0.5
    
    def _calculate_groundedness_score(self, response, chunks):
        """Calculate how well response is grounded in source documents"""
        try:
            if not chunks:
                return 0.0
            
            # Extract keywords from source chunks
            chunk_text = ' '.join(c.get('text', '') for c in chunks)
            chunk_keywords = set(re.findall(r'\w+', chunk_text.lower()))
            chunk_keywords = {w for w in chunk_keywords if len(w) > 4}
            
            # Extract keywords from response
            response_keywords = set(re.findall(r'\w+', response.lower()))
            response_keywords = {w for w in response_keywords if len(w) > 4}
            
            if not response_keywords:
                return 0.0
            
            # Calculate overlap (how many response keywords come from sources)
            overlap = len(chunk_keywords & response_keywords) / len(response_keywords)
            
            # Check for phrases that indicate grounding
            grounded_phrases = ['according to', 'based on', 'as mentioned', 'the document']
            has_grounded_phrases = any(p in response.lower() for p in grounded_phrases)
            
            score = overlap
            if has_grounded_phrases:
                score = min(score + 0.1, 1.0)
            
            return score
        
        except Exception as e:
            print(f"Error calculating groundedness: {str(e)}")
            return 0.5
    
    def _calculate_overall_score(self, scores):
        """Calculate weighted overall quality score"""
        weights = {
            'relevance': 0.25,
            'coherence': 0.15,
            'completeness': 0.20,
            'accuracy': 0.20,
            'conciseness': 0.10,
            'groundedness': 0.10
        }
        
        overall = sum(scores.get(k, 0) * v for k, v in weights.items())
        return overall
    
    def _store_quality_metrics(self, scores, metadata=None):
        """Store quality metrics in DynamoDB"""
        try:
            metric_id = str(uuid.uuid4())
            timestamp = int(datetime.utcnow().timestamp())
            
            item = {
                'metric_id': metric_id,
                'timestamp': timestamp,
                'metric_type': 'quality_evaluation',
                'date': datetime.utcnow().strftime('%Y-%m-%d'),
                'scores': scores,
                'iso_timestamp': datetime.utcnow().isoformat(),
                'ttl': timestamp + (90 * 24 * 60 * 60)  # 90 days
            }
            
            if metadata:
                item['metadata'] = metadata
            
            self.quality_metrics_table.put_item(Item=item)
        
        except Exception as e:
            print(f"Error storing quality metrics: {str(e)}")
    
    def _send_quality_metrics(self, scores):
        """Send quality metrics to CloudWatch"""
        try:
            metric_data = []
            
            for metric_name, value in scores.items():
                if metric_name != 'error':
                    metric_data.append({
                        'MetricName': f'{metric_name.capitalize()}Score',
                        'Value': value,
                        'Unit': 'None',
                        'Timestamp': datetime.utcnow()
                    })
            
            if metric_data:
                cloudwatch.put_metric_data(
                    Namespace='GenAI/Quality',
                    MetricData=metric_data
                )
        
        except Exception as e:
            print(f"Error sending quality metrics: {str(e)}")
    
    def collect_user_feedback(self, request_id, user_id, feedback_type, rating=None, comment=None):
        """
        Phase 6: User Feedback Collection
        Collect and store user feedback
        """
        try:
            feedback_id = str(uuid.uuid4())
            timestamp = int(datetime.utcnow().timestamp())
            
            item = {
                'feedback_id': feedback_id,
                'timestamp': timestamp,
                'request_id': request_id,
                'user_id': user_id or 'anonymous',
                'feedback_type': feedback_type,  # 'thumbs_up', 'thumbs_down', 'rating', 'comment'
                'iso_timestamp': datetime.utcnow().isoformat(),
                'ttl': timestamp + (180 * 24 * 60 * 60)  # 180 days
            }
            
            if rating is not None:
                item['rating'] = int(rating)
            
            if comment:
                item['comment'] = comment
                item['comment_length'] = len(comment)
            
            # Store in DynamoDB
            self.feedback_table.put_item(Item=item)
            
            # Send CloudWatch metrics
            self._send_feedback_metrics(feedback_type, rating)
            
            # Log to CloudWatch Logs
            self._log_feedback_event(item)
            
            return feedback_id
        
        except Exception as e:
            print(f"Error collecting feedback: {str(e)}")
            return None
    
    def _send_feedback_metrics(self, feedback_type, rating):
        """Send feedback metrics to CloudWatch"""
        try:
            metric_data = []
            
            if feedback_type == 'thumbs_up':
                metric_data.append({
                    'MetricName': 'ThumbsUp',
                    'Value': 1,
                    'Unit': 'Count'
                })
            elif feedback_type == 'thumbs_down':
                metric_data.append({
                    'MetricName': 'ThumbsDown',
                    'Value': 1,
                    'Unit': 'Count'
                })
            
            if rating is not None:
                metric_data.append({
                    'MetricName': 'AverageRating',
                    'Value': rating,
                    'Unit': 'None'
                })
            
            if metric_data:
                cloudwatch.put_metric_data(
                    Namespace='GenAI/Quality',
                    MetricData=metric_data
                )
        
        except Exception as e:
            print(f"Error sending feedback metrics: {str(e)}")
    
    def _log_feedback_event(self, feedback_item):
        """Log feedback event to CloudWatch Logs"""
        try:
            logs_client.put_log_events(
                logGroupName=self.log_group,
                logStreamName=f"user_feedback/{datetime.utcnow().strftime('%Y/%m/%d')}",
                logEvents=[{
                    'timestamp': int(datetime.utcnow().timestamp() * 1000),
                    'message': json.dumps({
                        'feedback_type': 'user_feedback',
                        'feedback_id': feedback_item['feedback_id'],
                        'rating': feedback_item.get('rating'),
                        'has_comment': 'comment' in feedback_item
                    })
                }]
            )
        except logs_client.exceptions.ResourceNotFoundException:
            # Create log stream if needed
            try:
                logs_client.create_log_stream(
                    logGroupName=self.log_group,
                    logStreamName=f"user_feedback/{datetime.utcnow().strftime('%Y/%m/%d')}"
                )
                # Retry
                logs_client.put_log_events(
                    logGroupName=self.log_group,
                    logStreamName=f"user_feedback/{datetime.utcnow().strftime('%Y/%m/%d')}",
                    logEvents=[{
                        'timestamp': int(datetime.utcnow().timestamp() * 1000),
                        'message': json.dumps({
                            'feedback_type': 'user_feedback',
                            'feedback_id': feedback_item['feedback_id'],
                            'rating': feedback_item.get('rating'),
                            'has_comment': 'comment' in feedback_item
                        })
                    }]
                )
            except Exception as e:
                print(f"Error creating log stream: {str(e)}")
        except Exception as e:
            print(f"Error logging feedback: {str(e)}")
    
    def calculate_performance_metrics(self, latency, tokens_prompt, tokens_response, cost, cached):
        """
        Phase 6: Performance Metrics Collection
        Calculate and send performance metrics
        """
        try:
            # Send latency metrics
            cloudwatch.put_metric_data(
                Namespace='GenAI/Performance',
                MetricData=[
                    {
                        'MetricName': 'QueryLatency',
                        'Value': latency * 1000,  # Convert to ms
                        'Unit': 'Milliseconds'
                    },
                    {
                        'MetricName': 'TokensPerSecond',
                        'Value': (tokens_prompt + tokens_response) / max(latency, 0.001),
                        'Unit': 'Count/Second'
                    },
                    {
                        'MetricName': 'CostPerQuery',
                        'Value': cost,
                        'Unit': 'None'
                    }
                ]
            )
            
            # Cache metrics
            if cached:
                cloudwatch.put_metric_data(
                    Namespace='GenAI/Performance',
                    MetricData=[{
                        'MetricName': 'CacheHits',
                        'Value': 1,
                        'Unit': 'Count'
                    }]
                )
            else:
                cloudwatch.put_metric_data(
                    Namespace='GenAI/Performance',
                    MetricData=[{
                        'MetricName': 'CacheMisses',
                        'Value': 1,
                        'Unit': 'Count'
                    }]
                )
            
            # Calculate cache hit rate (done by CloudWatch math expressions in dashboard)
        
        except Exception as e:
            print(f"Error calculating performance metrics: {str(e)}")
    
    def log_error_metric(self, error_type, error_message):
        """Log error metrics for monitoring"""
        try:
            cloudwatch.put_metric_data(
                Namespace='GenAI/Quality',
                MetricData=[
                    {
                        'MetricName': 'ErrorRate',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'ErrorType', 'Value': error_type}
                        ]
                    }
                ]
            )
        except Exception as e:
            print(f"Error logging error metric: {str(e)}")
    
    def log_success_metric(self):
        """Log success metrics"""
        try:
            cloudwatch.put_metric_data(
                Namespace='GenAI/Quality',
                MetricData=[{
                    'MetricName': 'SuccessRate',
                    'Value': 100,
                    'Unit': 'Percent'
                }]
            )
        except Exception as e:
            print(f"Error logging success metric: {str(e)}")

