import json
import boto3
import os

def lambda_handler(event, context):
    # Get the S3 object
    s3_client = boto3.client('s3')
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Only process image files
    if not key.lower().endswith(('.png', '.jpg', '.jpeg')):
        return {
            'statusCode': 200,
            'body': json.dumps('Not an image file')
        }
    
    try:
        # Extract text from the image using Amazon Textract
        textract = boto3.client('textract')
        response = textract.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        )
        
        # Extract the text
        extracted_text = ""
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                extracted_text += item['Text'] + "\n"
        
        # Analyze the image using Amazon Rekognition
        rekognition = boto3.client('rekognition')
        
        # Detect labels
        min_confidence = float(os.environ.get('MIN_CONFIDENCE', '70'))
        label_response = rekognition.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            MaxLabels=10,
            MinConfidence=min_confidence
        )
        
        # Detect text (as a backup to Textract)
        text_response = rekognition.detect_text(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        )
        
        # Combine the results
        processed_image = {
            'image_key': key,
            'extracted_text': extracted_text,
            'labels': [
                {
                    'Name': label['Name'],
                    'Confidence': label['Confidence']
                }
                for label in label_response['Labels']
            ],
            'detected_text': [
                {
                    'Text': text['DetectedText'],
                    'Confidence': text['Confidence'],
                    'Type': text['Type']
                }
                for text in text_response['TextDetections'] 
                if text['Type'] == 'LINE'
            ],
            'metadata': {
                'product_id': os.path.basename(key).split('_')[0] if '_' in os.path.basename(key) else ''
            }
        }
        
        # Save processed results
        base_name = os.path.splitext(os.path.basename(key))[0]
        processed_key = f"processed-data/images/{base_name}_processed.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=processed_key,
            Body=json.dumps(processed_image),
            ContentType='application/json'
        )
        
        print(f"Successfully processed image: {processed_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully processed image')
        }
        
    except Exception as e:
        print(f"Error processing {key}: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

