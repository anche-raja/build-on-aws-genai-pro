"""
Analytics Exporter Lambda
Phase 6: Weekly analytics export to S3
"""

import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Initialize tables
quality_metrics_table = dynamodb.Table(os.environ['QUALITY_METRICS_TABLE'])
user_feedback_table = dynamodb.Table(os.environ['USER_FEEDBACK_TABLE'])
evaluation_table = dynamodb.Table(os.environ['EVALUATION_TABLE'])
audit_trail_table = dynamodb.Table(os.environ['AUDIT_TRAIL_TABLE'])


def handler(event, context):
    """Export analytics data to S3 weekly"""
    try:
        # Calculate date range (last 7 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        print(f"Exporting analytics for {start_date.date()} to {end_date.date()}")
        
        # Collect analytics data
        analytics_data = {
            'export_id': f"analytics-{end_date.strftime('%Y-%m-%d')}",
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'exported_at': datetime.utcnow().isoformat(),
            'data': {}
        }
        
        # Export quality metrics
        analytics_data['data']['quality_metrics'] = export_quality_metrics(start_date, end_date)
        
        # Export user feedback
        analytics_data['data']['user_feedback'] = export_user_feedback(start_date, end_date)
        
        # Export evaluations
        analytics_data['data']['evaluations'] = export_evaluations(start_date, end_date)
        
        # Export audit summary
        analytics_data['data']['audit_summary'] = export_audit_summary(start_date, end_date)
        
        # Store in S3
        export_key = store_analytics_export(analytics_data, end_date)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Analytics export completed successfully',
                'export_key': export_key,
                'date_range': f"{start_date.date()} to {end_date.date()}"
            })
        }
    
    except Exception as e:
        print(f"Error exporting analytics: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def export_quality_metrics(start_date, end_date):
    """Export quality metrics from DynamoDB"""
    try:
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        items = []
        last_evaluated_key = None
        
        while True:
            query_params = {
                'IndexName': 'MetricTypeIndex',
                'KeyConditionExpression': 'metric_type = :mt AND #ts BETWEEN :start AND :end',
                'ExpressionAttributeNames': {'#ts': 'timestamp'},
                'ExpressionAttributeValues': {
                    ':mt': 'quality_evaluation',
                    ':start': start_ts,
                    ':end': end_ts
                }
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = quality_metrics_table.query(**query_params)
            items.extend(response.get('Items', []))
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        print(f"Exported {len(items)} quality metrics")
        return items
    
    except Exception as e:
        print(f"Error exporting quality metrics: {str(e)}")
        return []


def export_user_feedback(start_date, end_date):
    """Export user feedback from DynamoDB"""
    try:
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        items = []
        last_evaluated_key = None
        
        while True:
            scan_params = {
                'FilterExpression': '#ts BETWEEN :start AND :end',
                'ExpressionAttributeNames': {'#ts': 'timestamp'},
                'ExpressionAttributeValues': {
                    ':start': start_ts,
                    ':end': end_ts
                }
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = user_feedback_table.scan(**scan_params)
            items.extend(response.get('Items', []))
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        print(f"Exported {len(items)} feedback items")
        return items
    
    except Exception as e:
        print(f"Error exporting user feedback: {str(e)}")
        return []


def export_evaluations(start_date, end_date):
    """Export evaluation data from DynamoDB"""
    try:
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        items = []
        last_evaluated_key = None
        
        while True:
            scan_params = {
                'FilterExpression': '#ts BETWEEN :start AND :end',
                'ExpressionAttributeNames': {'#ts': 'timestamp'},
                'ExpressionAttributeValues': {
                    ':start': start_ts,
                    ':end': end_ts
                }
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = evaluation_table.scan(**scan_params)
            items.extend(response.get('Items', []))
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        print(f"Exported {len(items)} evaluations")
        return items
    
    except Exception as e:
        print(f"Error exporting evaluations: {str(e)}")
        return []


def export_audit_summary(start_date, end_date):
    """Export audit trail summary"""
    try:
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        items = []
        last_evaluated_key = None
        
        # Get sample of audit events (full export done by audit_exporter)
        scan_params = {
            'FilterExpression': '#ts BETWEEN :start AND :end',
            'ExpressionAttributeNames': {'#ts': 'timestamp'},
            'ExpressionAttributeValues': {
                ':start': start_ts,
                ':end': end_ts
            },
            'Limit': 1000  # Sample only
        }
        
        response = audit_trail_table.scan(**scan_params)
        items = response.get('Items', [])
        
        # Aggregate summary
        summary = {
            'total_events': len(items),
            'events_by_type': {},
            'events_by_severity': {}
        }
        
        for item in items:
            event_type = item.get('event_type', 'unknown')
            severity = item.get('severity', 'INFO')
            
            summary['events_by_type'][event_type] = summary['events_by_type'].get(event_type, 0) + 1
            summary['events_by_severity'][severity] = summary['events_by_severity'].get(severity, 0) + 1
        
        print(f"Exported audit summary with {len(items)} sample events")
        return summary
    
    except Exception as e:
        print(f"Error exporting audit summary: {str(e)}")
        return {}


def store_analytics_export(data, date):
    """Store analytics export in S3"""
    try:
        bucket = os.environ['ANALYTICS_BUCKET']
        key = f"analytics-exports/{date.strftime('%Y/%m')}/export-{date.strftime('%Y-%m-%d')}.json"
        
        # Convert Decimal to float for JSON serialization
        data_json = json.dumps(data, default=decimal_default, indent=2)
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data_json,
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        print(f"Analytics export stored at s3://{bucket}/{key}")
        return key
    
    except Exception as e:
        print(f"Error storing analytics export: {str(e)}")
        return None


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError
