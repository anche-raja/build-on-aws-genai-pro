import json
import boto3
import os
import uuid

def lambda_handler(event, context):
    # Get the S3 object
    s3_client = boto3.client('s3')
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Only process audio files
    if not key.lower().endswith(('.mp3', '.wav', '.flac')):
        return {
            'statusCode': 200,
            'body': json.dumps('Not an audio file')
        }
    
    try:
        # Start a transcription job
        transcribe = boto3.client('transcribe')
        job_name = f"transcribe-{uuid.uuid4()}"
        
        # Get file extension
        file_extension = os.path.splitext(key)[1][1:].lower()
        # Map extension to media format
        media_format_map = {
            'mp3': 'mp3',
            'wav': 'wav',
            'flac': 'flac',
            'mp4': 'mp4'
        }
        media_format = media_format_map.get(file_extension, 'mp3')
        
        # Define output location
        output_key = f"transcriptions/{os.path.splitext(os.path.basename(key))[0]}.json"
        
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={
                'MediaFileUri': f"s3://{bucket}/{key}"
            },
            MediaFormat=media_format,
            LanguageCode='en-US',
            OutputBucketName=bucket,
            OutputKey=output_key,
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 2  # Assuming customer and agent
            }
        )
        
        print(f"Started transcription job: {job_name}")
        print(f"Output will be saved to: s3://{bucket}/{output_key}")
        
        # Store job metadata for the next Lambda to process
        metadata = {
            'transcription_job_name': job_name,
            'audio_key': key,
            'output_key': output_key,
            'bucket': bucket
        }
        
        metadata_key = f"processing-metadata/{os.path.splitext(os.path.basename(key))[0]}_metadata.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=json.dumps(metadata),
            ContentType='application/json'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Transcription job started',
                'job_name': job_name,
                'output_key': output_key
            })
        }
        
    except Exception as e:
        print(f"Error processing {key}: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

