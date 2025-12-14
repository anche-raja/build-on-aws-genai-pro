"""
Audit Exporter Lambda
Phase 5: Daily audit log export to S3
"""

import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Initialize table
audit_trail_table = dynamodb.Table(os.environ['AUDIT_TRAIL_TABLE'])


def handler(event, context):
    """Export daily audit logs to S3"""
    try:
        # Calculate yesterday's date
        yesterday = datetime.utcnow() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')
        
        print(f"Exporting audit logs for {date_str}")
        
        # Export audit logs
        export_key = export_audit_logs(date_str)
        
        if export_key:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Audit logs exported successfully',
                    'export_key': export_key,
                    'date': date_str
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to export audit logs'
                })
            }
    
    except Exception as e:
        print(f"Error in audit export handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def export_audit_logs(date_str):
    """
    Export all audit logs for a specific date to S3
    """
    try:
        # Parse date
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        start_timestamp = int(target_date.timestamp())
        end_timestamp = start_timestamp + (24 * 60 * 60)
        
        print(f"Scanning audit trail from {start_timestamp} to {end_timestamp}")
        
        # Query all events for the date
        events = []
        last_evaluated_key = None
        
        while True:
            scan_params = {
                'FilterExpression': '#ts BETWEEN :start AND :end',
                'ExpressionAttributeNames': {'#ts': 'timestamp'},
                'ExpressionAttributeValues': {
                    ':start': start_timestamp,
                    ':end': end_timestamp
                }
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = audit_trail_table.scan(**scan_params)
            events.extend(response.get('Items', []))
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        print(f"Found {len(events)} audit events for {date_str}")
        
        # Create export data structure
        export_data = {
            'export_id': f"audit-export-{date_str}",
            'date': date_str,
            'exported_at': datetime.utcnow().isoformat(),
            'event_count': len(events),
            'events': events,
            'summary': generate_summary(events)
        }
        
        # Export to S3
        bucket = os.environ['AUDIT_LOGS_BUCKET']
        export_key = f"audit-exports/{target_date.strftime('%Y/%m')}/{date_str}/audit-log.json"
        
        # Convert Decimal to float for JSON serialization
        export_json = json.dumps(export_data, indent=2, default=decimal_default)
        
        s3.put_object(
            Bucket=bucket,
            Key=export_key,
            Body=export_json,
            ContentType='application/json',
            ServerSideEncryption='AES256',
            Metadata={
                'date': date_str,
                'event-count': str(len(events)),
                'exported-at': datetime.utcnow().isoformat()
            }
        )
        
        print(f"Exported {len(events)} audit events to s3://{bucket}/{export_key}")
        
        # Also create a summary file
        summary_key = f"audit-exports/{target_date.strftime('%Y/%m')}/{date_str}/summary.json"
        s3.put_object(
            Bucket=bucket,
            Key=summary_key,
            Body=json.dumps(export_data['summary'], indent=2, default=decimal_default),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        return export_key
    
    except Exception as e:
        print(f"Error exporting audit logs: {str(e)}")
        return None


def generate_summary(events):
    """Generate summary statistics from audit events"""
    summary = {
        'total_events': len(events),
        'events_by_type': {},
        'events_by_severity': {},
        'events_by_user': {},
        'high_severity_events': [],
        'pii_detections': 0,
        'guardrail_blocks': 0,
        'total_queries': 0
    }
    
    for event in events:
        # Count by type
        event_type = event.get('event_type', 'unknown')
        summary['events_by_type'][event_type] = summary['events_by_type'].get(event_type, 0) + 1
        
        # Count by severity
        severity = event.get('severity', 'INFO')
        summary['events_by_severity'][severity] = summary['events_by_severity'].get(severity, 0) + 1
        
        # Count by user
        user_id = event.get('user_id', 'anonymous')
        summary['events_by_user'][user_id] = summary['events_by_user'].get(user_id, 0) + 1
        
        # Track high severity events
        if severity in ['HIGH', 'CRITICAL']:
            summary['high_severity_events'].append({
                'audit_id': event.get('audit_id'),
                'event_type': event_type,
                'severity': severity,
                'timestamp': event.get('iso_timestamp'),
                'user_id': user_id
            })
        
        # Count specific event types
        if event_type == 'PII_DETECTED':
            summary['pii_detections'] += 1
        elif event_type in ['GUARDRAIL_BLOCKED', 'CONTENT_BLOCKED', 'RESPONSE_BLOCKED']:
            summary['guardrail_blocks'] += 1
        elif event_type == 'QUERY_PROCESSED':
            summary['total_queries'] += 1
    
    # Calculate percentages
    if summary['total_events'] > 0:
        summary['pii_detection_rate'] = (summary['pii_detections'] / summary['total_events']) * 100
        summary['guardrail_block_rate'] = (summary['guardrail_blocks'] / summary['total_events']) * 100
    
    return summary


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


# Alternative handler name for backward compatibility
export_handler = handler
