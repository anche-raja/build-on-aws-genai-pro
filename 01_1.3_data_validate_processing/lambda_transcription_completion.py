import json
import boto3
import os

def lambda_handler(event, context):
    """
    This Lambda is triggered by EventBridge when a Transcribe job completes.
    It processes the transcription with Comprehend.
    """
    # Get transcription job details from EventBridge event
    detail = event.get('detail', {})
    job_name = detail.get('TranscriptionJobName')
    job_status = detail.get('TranscriptionJobStatus')
    
    if job_status != 'COMPLETED':
        print(f"Transcription job {job_name} failed or not completed: {job_status}")
        return {
            'statusCode': 200,
            'body': json.dumps(f"Job not completed: {job_status}")
        }
    
    try:
        s3_client = boto3.client('s3')
        transcribe = boto3.client('transcribe')
        
        # Get job details
        job_details = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        transcript_uri = job_details['TranscriptionJob']['Transcript']['TranscriptFileUri']
        
        # Parse S3 URI to get bucket and key
        # Format: https://s3.region.amazonaws.com/bucket/key
        uri_parts = transcript_uri.replace('https://', '').split('/')
        bucket = uri_parts[0].split('.')[0] if '.' in uri_parts[0] else uri_parts[0]
        key = '/'.join(uri_parts[1:])
        
        # Get the transcription file
        response = s3_client.get_object(Bucket=bucket, Key=key)
        transcription = json.loads(response['Body'].read().decode('utf-8'))
        
        # Extract the transcript text
        transcript = transcription['results']['transcripts'][0]['transcript']
        
        # Use Amazon Comprehend for sentiment analysis
        comprehend = boto3.client('comprehend')
        sentiment_response = comprehend.detect_sentiment(
            Text=transcript[:5000],  # Comprehend has 5KB limit
            LanguageCode='en'
        )
        
        # Detect key phrases
        key_phrases_response = comprehend.detect_key_phrases(
            Text=transcript[:5000],
            LanguageCode='en'
        )
        
        # Combine the results
        processed_call = {
            'audio_key': job_details['TranscriptionJob']['Media']['MediaFileUri'],
            'transcript': transcript,
            'speakers': transcription['results'].get('speaker_labels', {}).get('segments', []),
            'sentiment': sentiment_response['Sentiment'],
            'sentiment_scores': sentiment_response['SentimentScore'],
            'key_phrases': key_phrases_response['KeyPhrases'],
            'metadata': {
                'job_name': job_name,
                'duration': job_details['TranscriptionJob'].get('MediaSampleRateHertz', 0)
            }
        }
        
        # Save processed results
        processed_key = f"processed-data/audio/{job_name}_processed.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=processed_key,
            Body=json.dumps(processed_call),
            ContentType='application/json'
        )
        
        print(f"Successfully processed transcription: {processed_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully processed audio')
        }
        
    except Exception as e:
        print(f"Error processing transcription {job_name}: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

