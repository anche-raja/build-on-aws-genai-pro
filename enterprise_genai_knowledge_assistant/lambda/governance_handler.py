"""
Governance Handler Module
Phase 5: Safety and Governance Features
"""

import json
import boto3
import uuid
from datetime import datetime
import hashlib

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sns = boto3.client('sns')
cloudwatch = boto3.client('cloudwatch')
logs_client = boto3.client('logs')
comprehend = boto3.client('comprehend')


class GovernanceHandler:
    """Handles all governance, safety, and compliance operations"""
    
    def __init__(self, audit_table_name, audit_bucket, sns_topic, log_group):
        self.audit_table = dynamodb.Table(audit_table_name)
        self.audit_bucket = audit_bucket
        self.sns_topic = sns_topic
        self.log_group = log_group
    
    def detect_and_redact_pii(self, text, user_id=None):
        """
        Phase 5: PII Detection and Redaction
        Detects PII and returns redacted text
        """
        try:
            # Detect PII entities
            response = comprehend.detect_pii_entities(
                Text=text[:5000],  # Comprehend limit
                LanguageCode='en'
            )
            
            entities = response.get('Entities', [])
            
            if not entities:
                return {
                    'original_text': text,
                    'redacted_text': text,
                    'has_pii': False,
                    'entities': []
                }
            
            # Sort entities by position (reverse order for replacement)
            entities_sorted = sorted(entities, key=lambda x: x['BeginOffset'], reverse=True)
            
            # Redact PII
            redacted_text = text
            pii_types = []
            
            for entity in entities_sorted:
                entity_type = entity['Type']
                start = entity['BeginOffset']
                end = entity['EndOffset']
                
                # Replace with placeholder
                placeholder = f"[{entity_type}]"
                redacted_text = redacted_text[:start] + placeholder + redacted_text[end:]
                pii_types.append(entity_type)
            
            # Log PII detection event
            self.log_audit_event(
                event_type='PII_DETECTED',
                user_id=user_id,
                details={
                    'pii_types': list(set(pii_types)),
                    'entity_count': len(entities),
                    'text_length': len(text)
                },
                severity='HIGH'
            )
            
            # Send CloudWatch metric
            cloudwatch.put_metric_data(
                Namespace='GenAI/Governance',
                MetricData=[{
                    'MetricName': 'PIIDetected',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'PIIType', 'Value': ','.join(set(pii_types))}
                    ]
                }]
            )
            
            return {
                'original_text': text,
                'redacted_text': redacted_text,
                'has_pii': True,
                'entities': entities,
                'pii_types': list(set(pii_types))
            }
        
        except Exception as e:
            print(f"Error in PII detection: {str(e)}")
            return {
                'original_text': text,
                'redacted_text': text,
                'has_pii': False,
                'entities': [],
                'error': str(e)
            }
    
    def apply_guardrails(self, text, guardrail_id, guardrail_version, source_type='INPUT'):
        """
        Phase 5: Amazon Bedrock Guardrails
        Apply content safety guardrails
        """
        try:
            bedrock_runtime = boto3.client('bedrock-runtime')
            
            response = bedrock_runtime.apply_guardrail(
                guardrailIdentifier=guardrail_id,
                guardrailVersion=guardrail_version,
                source=source_type,
                content=[{
                    'text': {'text': text}
                }]
            )
            
            action = response.get('action')  # NONE or GUARDRAIL_INTERVENED
            
            if action == 'GUARDRAIL_INTERVENED':
                # Guardrail blocked the content
                assessments = response.get('assessments', [])
                
                # Log guardrail intervention
                self.log_audit_event(
                    event_type='GUARDRAIL_BLOCKED',
                    details={
                        'source': source_type,
                        'assessments': assessments,
                        'text_hash': hashlib.md5(text.encode()).hexdigest()
                    },
                    severity='MEDIUM'
                )
                
                # Send metric
                cloudwatch.put_metric_data(
                    Namespace='GenAI/Governance',
                    MetricData=[{
                        'MetricName': 'GuardrailBlocked',
                        'Value': 1,
                        'Unit': 'Count'
                    }]
                )
                
                return {
                    'allowed': False,
                    'action': action,
                    'assessments': assessments
                }
            
            return {
                'allowed': True,
                'action': action
            }
        
        except Exception as e:
            print(f"Error applying guardrails: {str(e)}")
            # Fail open - allow content but log error
            return {
                'allowed': True,
                'error': str(e)
            }
    
    def log_audit_event(self, event_type, user_id=None, details=None, severity='INFO'):
        """
        Phase 5: Audit Trail
        Log all governance events for compliance
        """
        try:
            audit_id = str(uuid.uuid4())
            timestamp = int(datetime.utcnow().timestamp())
            
            # Store in DynamoDB
            item = {
                'audit_id': audit_id,
                'timestamp': timestamp,
                'event_type': event_type,
                'user_id': user_id or 'anonymous',
                'severity': severity,
                'details': json.dumps(details) if details else '{}',
                'iso_timestamp': datetime.utcnow().isoformat(),
                'ttl': timestamp + (7 * 365 * 24 * 60 * 60)  # 7 years
            }
            
            self.audit_table.put_item(Item=item)
            
            # Also log to CloudWatch for real-time monitoring
            try:
                logs_client.put_log_events(
                    logGroupName=self.log_group,
                    logStreamName=f"{event_type}/{datetime.utcnow().strftime('%Y/%m/%d')}",
                    logEvents=[{
                        'timestamp': timestamp * 1000,
                        'message': json.dumps({
                            'audit_id': audit_id,
                            'event_type': event_type,
                            'user_id': user_id,
                            'severity': severity,
                            'details': details
                        })
                    }]
                )
            except logs_client.exceptions.ResourceNotFoundException:
                # Create log stream if it doesn't exist
                try:
                    logs_client.create_log_stream(
                        logGroupName=self.log_group,
                        logStreamName=f"{event_type}/{datetime.utcnow().strftime('%Y/%m/%d')}"
                    )
                    # Retry
                    logs_client.put_log_events(
                        logGroupName=self.log_group,
                        logStreamName=f"{event_type}/{datetime.utcnow().strftime('%Y/%m/%d')}",
                        logEvents=[{
                            'timestamp': timestamp * 1000,
                            'message': json.dumps({
                                'audit_id': audit_id,
                                'event_type': event_type,
                                'user_id': user_id,
                                'severity': severity,
                                'details': details
                            })
                        }]
                    )
                except Exception as e:
                    print(f"Error creating log stream: {str(e)}")
            
            # Archive to S3 for long-term storage
            s3_key = f"audit-logs/{datetime.utcnow().strftime('%Y/%m/%d')}/{audit_id}.json"
            s3.put_object(
                Bucket=self.audit_bucket,
                Key=s3_key,
                Body=json.dumps(item),
                ServerSideEncryption='AES256'
            )
            
            # Send alert for high severity events
            if severity in ['HIGH', 'CRITICAL']:
                self.send_compliance_alert(event_type, details, severity)
            
            return audit_id
        
        except Exception as e:
            print(f"Error logging audit event: {str(e)}")
            return None
    
    def send_compliance_alert(self, event_type, details, severity):
        """Send SNS alert for compliance events"""
        try:
            message = {
                'event_type': event_type,
                'severity': severity,
                'timestamp': datetime.utcnow().isoformat(),
                'details': details
            }
            
            sns.publish(
                TopicArn=self.sns_topic,
                Subject=f"[{severity}] GenAI Governance Alert: {event_type}",
                Message=json.dumps(message, indent=2)
            )
        except Exception as e:
            print(f"Error sending compliance alert: {str(e)}")
    
    def log_query_event(self, request_id, user_id, query, response, model_id, 
                       has_pii, guardrail_result, cost, latency):
        """
        Phase 5: Comprehensive Query Logging
        Log every query for compliance and audit
        """
        details = {
            'request_id': request_id,
            'query_hash': hashlib.md5(query.encode()).hexdigest(),
            'query_length': len(query),
            'response_length': len(response),
            'model_id': model_id,
            'has_pii': has_pii,
            'guardrail_blocked': not guardrail_result.get('allowed', True),
            'cost': cost,
            'latency': latency
        }
        
        severity = 'HIGH' if has_pii or not guardrail_result.get('allowed', True) else 'INFO'
        
        return self.log_audit_event(
            event_type='QUERY_PROCESSED',
            user_id=user_id,
            details=details,
            severity=severity
        )
    
    def get_audit_trail(self, user_id=None, event_type=None, start_time=None, end_time=None, limit=100):
        """
        Query audit trail for compliance reporting
        """
        try:
            if event_type:
                # Query by event type
                response = self.audit_table.query(
                    IndexName='EventTypeIndex',
                    KeyConditionExpression='event_type = :et',
                    ExpressionAttributeValues={':et': event_type},
                    ScanIndexForward=False,
                    Limit=limit
                )
            elif user_id:
                # Query by user
                response = self.audit_table.query(
                    IndexName='UserIndex',
                    KeyConditionExpression='user_id = :uid',
                    ExpressionAttributeValues={':uid': user_id},
                    ScanIndexForward=False,
                    Limit=limit
                )
            else:
                # Scan all (use sparingly)
                response = self.audit_table.scan(Limit=limit)
            
            return response.get('Items', [])
        
        except Exception as e:
            print(f"Error querying audit trail: {str(e)}")
            return []
    
    def generate_compliance_report(self, start_date, end_date):
        """
        Phase 5: Compliance Reporting
        Generate compliance report for a date range
        """
        try:
            # Query audit trail
            events = self.get_audit_trail(limit=10000)
            
            # Aggregate statistics
            report = {
                'report_id': str(uuid.uuid4()),
                'start_date': start_date,
                'end_date': end_date,
                'generated_at': datetime.utcnow().isoformat(),
                'statistics': {
                    'total_queries': 0,
                    'pii_detected': 0,
                    'guardrail_blocked': 0,
                    'total_cost': 0.0,
                    'avg_latency': 0.0,
                    'unique_users': set()
                },
                'events_by_type': {},
                'events_by_severity': {}
            }
            
            latencies = []
            
            for event in events:
                event_type = event.get('event_type')
                severity = event.get('severity', 'INFO')
                
                # Count by type
                report['events_by_type'][event_type] = report['events_by_type'].get(event_type, 0) + 1
                
                # Count by severity
                report['events_by_severity'][severity] = report['events_by_severity'].get(severity, 0) + 1
                
                # Parse details
                try:
                    details = json.loads(event.get('details', '{}'))
                    
                    if event_type == 'QUERY_PROCESSED':
                        report['statistics']['total_queries'] += 1
                        if details.get('has_pii'):
                            report['statistics']['pii_detected'] += 1
                        if details.get('guardrail_blocked'):
                            report['statistics']['guardrail_blocked'] += 1
                        report['statistics']['total_cost'] += details.get('cost', 0)
                        latencies.append(details.get('latency', 0))
                    
                    user_id = event.get('user_id')
                    if user_id and user_id != 'anonymous':
                        report['statistics']['unique_users'].add(user_id)
                
                except:
                    pass
            
            # Calculate averages
            if latencies:
                report['statistics']['avg_latency'] = sum(latencies) / len(latencies)
            
            report['statistics']['unique_users'] = len(report['statistics']['unique_users'])
            
            # Store report in S3
            report_key = f"compliance-reports/{start_date}/{report['report_id']}.json"
            s3.put_object(
                Bucket=self.audit_bucket,
                Key=report_key,
                Body=json.dumps(report, indent=2),
                ServerSideEncryption='AES256'
            )
            
            return report
        
        except Exception as e:
            print(f"Error generating compliance report: {str(e)}")
            return None
    
    def check_content_safety(self, text, guardrail_id, guardrail_version):
        """
        Phase 5: Content Safety Check
        Apply Bedrock guardrails before processing
        """
        try:
            bedrock_runtime = boto3.client('bedrock-runtime')
            
            # Apply guardrail to input
            response = bedrock_runtime.apply_guardrail(
                guardrailIdentifier=guardrail_id,
                guardrailVersion=guardrail_version,
                source='INPUT',
                content=[{
                    'text': {'text': text}
                }]
            )
            
            action = response.get('action')
            
            if action == 'GUARDRAIL_INTERVENED':
                assessments = response.get('assessments', [])
                
                # Log intervention
                self.log_audit_event(
                    event_type='CONTENT_BLOCKED',
                    details={
                        'reason': 'guardrail_intervention',
                        'assessments': assessments
                    },
                    severity='MEDIUM'
                )
                
                return {
                    'safe': False,
                    'action': action,
                    'message': 'Content blocked by safety guardrails',
                    'assessments': assessments
                }
            
            return {
                'safe': True,
                'action': action
            }
        
        except Exception as e:
            print(f"Error checking content safety: {str(e)}")
            # Fail open for availability
            return {
                'safe': True,
                'error': str(e)
            }
    
    def validate_response_safety(self, response_text, guardrail_id, guardrail_version):
        """
        Phase 5: Response Validation
        Validate generated response before returning to user
        """
        try:
            bedrock_runtime = boto3.client('bedrock-runtime')
            
            # Apply guardrail to output
            result = bedrock_runtime.apply_guardrail(
                guardrailIdentifier=guardrail_id,
                guardrailVersion=guardrail_version,
                source='OUTPUT',
                content=[{
                    'text': {'text': response_text}
                }]
            )
            
            action = result.get('action')
            
            if action == 'GUARDRAIL_INTERVENED':
                # Response blocked
                self.log_audit_event(
                    event_type='RESPONSE_BLOCKED',
                    details={
                        'reason': 'guardrail_intervention',
                        'assessments': result.get('assessments', [])
                    },
                    severity='HIGH'
                )
                
                return {
                    'safe': False,
                    'action': action,
                    'message': 'Response blocked by safety guardrails'
                }
            
            return {
                'safe': True,
                'action': action
            }
        
        except Exception as e:
            print(f"Error validating response safety: {str(e)}")
            # Fail open
            return {
                'safe': True,
                'error': str(e)
            }
    
    def log_model_invocation(self, model_id, prompt_tokens, response_tokens, cost, latency, user_id=None):
        """Log every model invocation for governance"""
        self.log_audit_event(
            event_type='MODEL_INVOKED',
            user_id=user_id,
            details={
                'model_id': model_id,
                'prompt_tokens': prompt_tokens,
                'response_tokens': response_tokens,
                'cost': cost,
                'latency': latency
            },
            severity='INFO'
        )
    
    def export_audit_logs_to_s3(self, date_str):
        """
        Export daily audit logs to S3 for archival
        """
        try:
            # Query all events for the date
            start_timestamp = int(datetime.strptime(date_str, '%Y-%m-%d').timestamp())
            end_timestamp = start_timestamp + (24 * 60 * 60)
            
            response = self.audit_table.scan(
                FilterExpression='#ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start': start_timestamp,
                    ':end': end_timestamp
                }
            )
            
            events = response.get('Items', [])
            
            # Export to S3
            export_key = f"audit-exports/{date_str}/audit-log.json"
            s3.put_object(
                Bucket=self.audit_bucket,
                Key=export_key,
                Body=json.dumps(events, indent=2, default=str),
                ServerSideEncryption='AES256'
            )
            
            print(f"Exported {len(events)} audit events to S3: {export_key}")
            return export_key
        
        except Exception as e:
            print(f"Error exporting audit logs: {str(e)}")
            return None

