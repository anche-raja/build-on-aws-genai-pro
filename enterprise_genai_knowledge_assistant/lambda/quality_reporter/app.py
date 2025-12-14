"""
Quality Reporter Lambda
Phase 6: Daily quality report generation
"""

import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sns = boto3.client('sns')

# Initialize tables
quality_metrics_table = dynamodb.Table(os.environ['QUALITY_METRICS_TABLE'])
user_feedback_table = dynamodb.Table(os.environ['USER_FEEDBACK_TABLE'])
evaluation_table = dynamodb.Table(os.environ['EVALUATION_TABLE'])


def handler(event, context):
    """Generate daily quality report"""
    try:
        # Calculate date range (yesterday)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        print(f"Generating quality report for {start_date.date()} to {end_date.date()}")
        
        # Generate report
        report = generate_quality_report(start_date, end_date)
        
        # Store report in S3
        report_key = store_report(report, start_date)
        
        # Send summary via SNS
        send_report_summary(report, report_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Quality report generated successfully',
                'report_key': report_key,
                'date': start_date.strftime('%Y-%m-%d')
            })
        }
    
    except Exception as e:
        print(f"Error generating quality report: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def generate_quality_report(start_date, end_date):
    """Generate comprehensive quality report"""
    report = {
        'report_id': f"quality-report-{start_date.strftime('%Y-%m-%d')}",
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': datetime.utcnow().isoformat(),
        'metrics': {},
        'feedback': {},
        'evaluation': {},
        'trends': {},
        'recommendations': []
    }
    
    # Get quality metrics
    report['metrics'] = get_quality_metrics(start_date, end_date)
    
    # Get user feedback
    report['feedback'] = get_user_feedback_summary(start_date, end_date)
    
    # Get evaluation data
    report['evaluation'] = get_evaluation_summary(start_date, end_date)
    
    # Calculate trends
    report['trends'] = calculate_trends(report['metrics'], report['feedback'])
    
    # Generate recommendations
    report['recommendations'] = generate_recommendations(report)
    
    return report


def get_quality_metrics(start_date, end_date):
    """Get quality metrics from DynamoDB"""
    try:
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        response = quality_metrics_table.query(
            IndexName='MetricTypeIndex',
            KeyConditionExpression='metric_type = :mt AND #ts BETWEEN :start AND :end',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':mt': 'quality_evaluation',
                ':start': start_ts,
                ':end': end_ts
            }
        )
        
        items = response.get('Items', [])
        
        if not items:
            return {'count': 0}
        
        # Aggregate scores
        scores = {
            'relevance': [],
            'coherence': [],
            'completeness': [],
            'accuracy': [],
            'conciseness': [],
            'groundedness': [],
            'overall': []
        }
        
        for item in items:
            item_scores = item.get('scores', {})
            for key in scores.keys():
                if key in item_scores:
                    scores[key].append(float(item_scores[key]))
        
        # Calculate averages
        metrics = {
            'count': len(items),
            'average_scores': {}
        }
        
        for key, values in scores.items():
            if values:
                metrics['average_scores'][key] = sum(values) / len(values)
        
        return metrics
    
    except Exception as e:
        print(f"Error getting quality metrics: {str(e)}")
        return {'count': 0, 'error': str(e)}


def get_user_feedback_summary(start_date, end_date):
    """Get user feedback summary"""
    try:
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        # Scan feedback table (in production, use date-based GSI)
        response = user_feedback_table.scan(
            FilterExpression='#ts BETWEEN :start AND :end',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':start': start_ts,
                ':end': end_ts
            }
        )
        
        items = response.get('Items', [])
        
        summary = {
            'total_feedback': len(items),
            'thumbs_up': 0,
            'thumbs_down': 0,
            'ratings': [],
            'comments': 0
        }
        
        for item in items:
            feedback_type = item.get('feedback_type', '')
            
            if feedback_type == 'thumbs_up':
                summary['thumbs_up'] += 1
            elif feedback_type == 'thumbs_down':
                summary['thumbs_down'] += 1
            
            if 'rating' in item:
                summary['ratings'].append(int(item['rating']))
            
            if 'comment' in item:
                summary['comments'] += 1
        
        # Calculate average rating
        if summary['ratings']:
            summary['average_rating'] = sum(summary['ratings']) / len(summary['ratings'])
        
        # Calculate satisfaction rate
        total_thumbs = summary['thumbs_up'] + summary['thumbs_down']
        if total_thumbs > 0:
            summary['satisfaction_rate'] = (summary['thumbs_up'] / total_thumbs) * 100
        
        return summary
    
    except Exception as e:
        print(f"Error getting feedback summary: {str(e)}")
        return {'total_feedback': 0, 'error': str(e)}


def get_evaluation_summary(start_date, end_date):
    """Get evaluation data summary"""
    try:
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        # Scan evaluation table
        response = evaluation_table.scan(
            FilterExpression='#ts BETWEEN :start AND :end',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':start': start_ts,
                ':end': end_ts
            }
        )
        
        items = response.get('Items', [])
        
        summary = {
            'total_queries': len(items),
            'total_cost': 0.0,
            'total_latency': 0.0,
            'total_tokens': 0,
            'model_usage': {}
        }
        
        for item in items:
            summary['total_cost'] += float(item.get('cost', 0))
            summary['total_latency'] += float(item.get('latency', 0))
            summary['total_tokens'] += int(item.get('prompt_tokens', 0)) + int(item.get('response_tokens', 0))
            
            model_id = item.get('model_id', 'unknown')
            summary['model_usage'][model_id] = summary['model_usage'].get(model_id, 0) + 1
        
        if items:
            summary['average_cost'] = summary['total_cost'] / len(items)
            summary['average_latency'] = summary['total_latency'] / len(items)
            summary['average_tokens'] = summary['total_tokens'] / len(items)
        
        return summary
    
    except Exception as e:
        print(f"Error getting evaluation summary: {str(e)}")
        return {'total_queries': 0, 'error': str(e)}


def calculate_trends(metrics, feedback):
    """Calculate trends and insights"""
    trends = {
        'quality_trend': 'stable',
        'satisfaction_trend': 'stable',
        'insights': []
    }
    
    # Analyze quality scores
    avg_scores = metrics.get('average_scores', {})
    overall_score = avg_scores.get('overall', 0)
    
    if overall_score > 0.8:
        trends['quality_trend'] = 'excellent'
        trends['insights'].append("Overall response quality is excellent (>0.8)")
    elif overall_score > 0.6:
        trends['quality_trend'] = 'good'
        trends['insights'].append("Overall response quality is good (0.6-0.8)")
    elif overall_score > 0:
        trends['quality_trend'] = 'needs_improvement'
        trends['insights'].append("Overall response quality needs improvement (<0.6)")
    
    # Analyze satisfaction
    satisfaction_rate = feedback.get('satisfaction_rate', 0)
    
    if satisfaction_rate > 80:
        trends['satisfaction_trend'] = 'high'
        trends['insights'].append(f"User satisfaction is high ({satisfaction_rate:.1f}%)")
    elif satisfaction_rate > 60:
        trends['satisfaction_trend'] = 'moderate'
        trends['insights'].append(f"User satisfaction is moderate ({satisfaction_rate:.1f}%)")
    elif satisfaction_rate > 0:
        trends['satisfaction_trend'] = 'low'
        trends['insights'].append(f"User satisfaction is low ({satisfaction_rate:.1f}%)")
    
    return trends


def generate_recommendations(report):
    """Generate actionable recommendations"""
    recommendations = []
    
    metrics = report.get('metrics', {})
    feedback = report.get('feedback', {})
    evaluation = report.get('evaluation', {})
    
    # Check quality scores
    avg_scores = metrics.get('average_scores', {})
    
    if avg_scores.get('relevance', 0) < 0.7:
        recommendations.append({
            'priority': 'high',
            'category': 'quality',
            'issue': 'Low relevance score',
            'recommendation': 'Review search algorithm and re-ranking logic'
        })
    
    if avg_scores.get('groundedness', 0) < 0.6:
        recommendations.append({
            'priority': 'high',
            'category': 'quality',
            'issue': 'Low groundedness score',
            'recommendation': 'Improve prompt to emphasize using source documents'
        })
    
    # Check satisfaction
    satisfaction_rate = feedback.get('satisfaction_rate', 0)
    if satisfaction_rate < 70:
        recommendations.append({
            'priority': 'high',
            'category': 'satisfaction',
            'issue': f'Low satisfaction rate ({satisfaction_rate:.1f}%)',
            'recommendation': 'Review negative feedback comments and address common issues'
        })
    
    # Check cost
    avg_cost = evaluation.get('average_cost', 0)
    if avg_cost > 0.02:
        recommendations.append({
            'priority': 'medium',
            'category': 'cost',
            'issue': f'High average cost per query (${avg_cost:.4f})',
            'recommendation': 'Consider increasing cache TTL or using simpler models for basic queries'
        })
    
    # Check latency
    avg_latency = evaluation.get('average_latency', 0)
    if avg_latency > 3.0:
        recommendations.append({
            'priority': 'medium',
            'category': 'performance',
            'issue': f'High average latency ({avg_latency:.2f}s)',
            'recommendation': 'Optimize search queries and consider caching strategies'
        })
    
    return recommendations


def store_report(report, date):
    """Store report in S3"""
    try:
        bucket = os.environ['ANALYTICS_BUCKET']
        key = f"quality-reports/{date.strftime('%Y/%m')}/report-{date.strftime('%Y-%m-%d')}.json"
        
        # Convert Decimal to float for JSON serialization
        report_json = json.dumps(report, default=decimal_default, indent=2)
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=report_json,
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        print(f"Report stored at s3://{bucket}/{key}")
        return key
    
    except Exception as e:
        print(f"Error storing report: {str(e)}")
        return None


def send_report_summary(report, report_key):
    """Send report summary via SNS"""
    try:
        sns_topic = os.environ['SNS_TOPIC']
        
        metrics = report.get('metrics', {})
        feedback = report.get('feedback', {})
        evaluation = report.get('evaluation', {})
        trends = report.get('trends', {})
        recommendations = report.get('recommendations', [])
        
        message = f"""
Daily Quality Report - {report.get('start_date', '')[:10]}

QUALITY METRICS:
- Total Evaluations: {metrics.get('count', 0)}
- Overall Quality Score: {metrics.get('average_scores', {}).get('overall', 0):.2f}
- Relevance: {metrics.get('average_scores', {}).get('relevance', 0):.2f}
- Coherence: {metrics.get('average_scores', {}).get('coherence', 0):.2f}
- Completeness: {metrics.get('average_scores', {}).get('completeness', 0):.2f}

USER FEEDBACK:
- Total Feedback: {feedback.get('total_feedback', 0)}
- Thumbs Up: {feedback.get('thumbs_up', 0)}
- Thumbs Down: {feedback.get('thumbs_down', 0)}
- Satisfaction Rate: {feedback.get('satisfaction_rate', 0):.1f}%
- Average Rating: {feedback.get('average_rating', 0):.2f}/5

PERFORMANCE:
- Total Queries: {evaluation.get('total_queries', 0)}
- Average Latency: {evaluation.get('average_latency', 0):.2f}s
- Average Cost: ${evaluation.get('average_cost', 0):.4f}
- Total Cost: ${evaluation.get('total_cost', 0):.2f}

TRENDS:
- Quality Trend: {trends.get('quality_trend', 'unknown')}
- Satisfaction Trend: {trends.get('satisfaction_trend', 'unknown')}

RECOMMENDATIONS ({len(recommendations)}):
"""
        
        for i, rec in enumerate(recommendations[:5], 1):
            message += f"\n{i}. [{rec['priority'].upper()}] {rec['issue']}\n   → {rec['recommendation']}\n"
        
        if len(recommendations) > 5:
            message += f"\n... and {len(recommendations) - 5} more recommendations\n"
        
        message += f"\nFull report: s3://{os.environ['ANALYTICS_BUCKET']}/{report_key}"
        
        sns.publish(
            TopicArn=sns_topic,
            Subject=f"Daily Quality Report - {report.get('start_date', '')[:10]}",
            Message=message
        )
        
        print("Report summary sent via SNS")
    
    except Exception as e:
        print(f"Error sending report summary: {str(e)}")


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

