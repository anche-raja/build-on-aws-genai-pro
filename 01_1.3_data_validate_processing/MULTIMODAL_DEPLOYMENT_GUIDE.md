# Multimodal Data Processing - Deployment Guide

Complete guide for deploying and testing the multimodal data processing pipeline.

## Prerequisites

- AWS Account with appropriate permissions
- Terraform ≥ 1.6
- Python 3.11+
- AWS CLI configured
- boto3, pandas (for SageMaker)

## Architecture Components

This deployment creates:
- **4 Lambda Functions**: Text processing, Image processing, Audio processing start, Audio processing completion
- **1 EventBridge Rule**: Triggers when Transcribe jobs complete
- **S3 Bucket**: With multiple event notifications for different file types
- **IAM Roles**: Separate roles for each Lambda with least-privilege permissions
- **CloudWatch Dashboard**: Monitors all processing pipelines

## Deployment Steps

### Step 1: Deploy Base Infrastructure

First, deploy the base infrastructure (if not already done):

```bash
cd 01_1.3_data_validate_processing/iac
terraform init
terraform plan
terraform apply
```

This creates:
- S3 bucket
- Initial text validation Lambda
- Glue database and crawler
- CloudWatch dashboard

### Step 2: Deploy Multimodal Processing

The multimodal Lambda functions are defined in `multimodal_lambdas.tf`:

```bash
# Apply the multimodal configuration
terraform apply
```

**Note**: S3 bucket notifications have dependencies. Terraform handles this automatically with `depends_on` blocks.

### Step 3: Register Glue Data Quality Rules

```bash
cd ..
python create_glue_data_quality_ruleset.py --region us-east-1
```

### Step 4: Verify Deployment

Check that all Lambda functions are created:

```bash
aws lambda list-functions --query 'Functions[?contains(FunctionName, `Processing`) || contains(FunctionName, `Validation`)].FunctionName'
```

Expected output:
```
[
  "TextValidationFunction",
  "TextProcessingFunction",
  "ImageProcessingFunction",
  "AudioProcessingFunction",
  "TranscriptionCompletionFunction"
]
```

Check S3 bucket notifications:

```bash
aws s3api get-bucket-notification-configuration --bucket customer-feedback-analysis-<initials>
```

## Testing the Pipeline

### Test 1: Text Review Processing

Upload a sample JSON review:

```bash
# Get your bucket name
BUCKET_NAME=$(terraform output -raw project_bucket_name 2>/dev/null || echo "customer-feedback-analysis-ars")

# Upload sample review
aws s3 cp sample-data/review1.json s3://${BUCKET_NAME}/raw-data/

# Wait 5-10 seconds, then check validation results
aws s3 ls s3://${BUCKET_NAME}/validation-results/

# Check processed results (if quality score >= 0.7)
aws s3 ls s3://${BUCKET_NAME}/processed-data/

# Download and view results
aws s3 cp s3://${BUCKET_NAME}/processed-data/review1_processed.json - | jq .
```

**Expected Output**:
```json
{
  "original_text": "I absolutely love this product!...",
  "entities": [
    {
      "Text": "product",
      "Type": "COMMERCIAL_ITEM",
      "Score": 0.95
    }
  ],
  "sentiment": "POSITIVE",
  "sentiment_scores": {
    "Positive": 0.98,
    "Negative": 0.01,
    "Neutral": 0.01,
    "Mixed": 0.00
  },
  "key_phrases": [
    {
      "Text": "excellent quality",
      "Score": 0.99
    }
  ],
  "metadata": {
    "product_id": "P98765",
    "customer_id": "C12345"
  }
}
```

### Test 2: Image Processing

**Option A: Create a simple test image**

Create a simple PNG with text using ImageMagick:

```bash
# Install ImageMagick if not available
# macOS: brew install imagemagick
# Ubuntu: sudo apt-get install imagemagick

# Create test image with text
convert -size 800x600 xc:white \
  -font Arial -pointsize 36 -fill black \
  -gravity center -annotate +0+0 "Product ID: P12345\nBarcode: 123456789\nMade in USA" \
  test_product_label.png

# Upload to S3
aws s3 cp test_product_label.png s3://${BUCKET_NAME}/raw-data/images/
```

**Option B: Use any product image**

```bash
# Download a sample product image or use your own
aws s3 cp /path/to/product_image.jpg s3://${BUCKET_NAME}/raw-data/images/
```

**Check results:**

```bash
# Wait 10-15 seconds for processing
aws s3 ls s3://${BUCKET_NAME}/processed-data/images/

# View results
aws s3 cp s3://${BUCKET_NAME}/processed-data/images/test_product_label_processed.json - | jq .
```

**Expected Output**:
```json
{
  "image_key": "raw-data/images/test_product_label.png",
  "extracted_text": "Product ID: P12345\nBarcode: 123456789\nMade in USA\n",
  "labels": [
    {
      "Name": "Text",
      "Confidence": 99.5
    },
    {
      "Name": "Label",
      "Confidence": 98.2
    }
  ],
  "detected_text": [
    {
      "Text": "Product ID: P12345",
      "Confidence": 99.8,
      "Type": "LINE"
    }
  ],
  "metadata": {
    "product_id": "test"
  }
}
```

### Test 3: Audio Processing

**Option A: Create TTS audio with AWS Polly**

```bash
# Create a sample customer service call script
cat > call_script.txt << 'EOF'
Hello, thank you for calling customer service. I'm calling about my recent order. The product arrived damaged and I need a replacement. I'm sorry to hear that. Let me process a replacement for you right away. Thank you so much for your help!
EOF

# Generate audio with Polly
aws polly synthesize-speech \
  --output-format mp3 \
  --voice-id Joanna \
  --text file://call_script.txt \
  sample_call.mp3

# Upload to S3
aws s3 cp sample_call.mp3 s3://${BUCKET_NAME}/raw-data/audio/
```

**Option B: Record your own audio**

Record a 30-60 second MP3/WAV file and upload:

```bash
aws s3 cp your_audio.mp3 s3://${BUCKET_NAME}/raw-data/audio/
```

**Check progress:**

```bash
# Check that transcription job started
aws transcribe list-transcription-jobs --max-results 5

# Wait for job to complete (can take 1-3 minutes)
# Check for transcription output
aws s3 ls s3://${BUCKET_NAME}/transcriptions/

# Check for processed output (after EventBridge triggers completion)
aws s3 ls s3://${BUCKET_NAME}/processed-data/audio/

# View results
aws s3 cp s3://${BUCKET_NAME}/processed-data/audio/transcribe-*_processed.json - | jq .
```

**Expected Output**:
```json
{
  "audio_key": "s3://bucket/raw-data/audio/sample_call.mp3",
  "transcript": "Hello, thank you for calling customer service...",
  "speakers": [
    {
      "speaker_label": "spk_0",
      "start_time": "0.0",
      "end_time": "3.5"
    }
  ],
  "sentiment": "POSITIVE",
  "sentiment_scores": {
    "Positive": 0.85,
    "Negative": 0.05,
    "Neutral": 0.10
  },
  "key_phrases": [
    {
      "Text": "customer service",
      "Score": 0.99
    }
  ]
}
```

### Test 4: Survey Processing

```bash
# Upload survey data
aws s3 cp sample-data/surveys.csv s3://${BUCKET_NAME}/raw-data/

# Run SageMaker processing job
python run_sagemaker_survey_job.py --bucket ${BUCKET_NAME} --region us-east-1
```

**Note**: This requires a SageMaker execution role. Create one if needed:

```bash
# Create SageMaker execution role (one-time setup)
aws iam create-role \
  --role-name SageMakerExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "sagemaker.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**Check results:**

```bash
# Wait for SageMaker job to complete
aws s3 ls s3://${BUCKET_NAME}/processed-data/surveys/

# View summaries
aws s3 cp s3://${BUCKET_NAME}/processed-data/surveys/survey_summaries.json - | jq '.[0:3]'

# View statistics
aws s3 cp s3://${BUCKET_NAME}/processed-data/surveys/survey_statistics.json - | jq .
```

## Monitoring and Logs

### CloudWatch Logs

View Lambda execution logs:

```bash
# Text processing logs
aws logs tail /aws/lambda/TextProcessingFunction --follow

# Image processing logs
aws logs tail /aws/lambda/ImageProcessingFunction --follow

# Audio processing logs
aws logs tail /aws/lambda/AudioProcessingFunction --follow
aws logs tail /aws/lambda/TranscriptionCompletionFunction --follow
```

### CloudWatch Dashboard

View the dashboard in AWS Console:

```bash
# Open dashboard URL
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=CustomerFeedbackQuality"
```

### Metrics

Check custom metrics:

```bash
# Text quality scores
aws cloudwatch get-metric-statistics \
  --namespace CustomerFeedback/TextQuality \
  --metric-name QualityScore \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

## Troubleshooting

### Lambda Function Errors

Check CloudWatch Logs for detailed error messages:

```bash
aws logs tail /aws/lambda/TextProcessingFunction --since 10m
```

Common issues:
- **Permission denied**: Check IAM role has required service permissions
- **Quality score too low**: Text validation score < 0.7, increase text quality
- **S3 key not found**: Check file paths and bucket names

### Transcribe Job Failures

Check transcription job status:

```bash
aws transcribe list-transcription-jobs --status FAILED --max-results 5
```

Common issues:
- **Unsupported format**: Use MP3, WAV, or FLAC
- **Audio too short**: Need at least 0.5 seconds
- **Poor audio quality**: Transcribe may fail on very low-quality audio

### EventBridge Not Triggering

Check EventBridge rule:

```bash
aws events describe-rule --name transcribe-job-completion
aws events list-targets-by-rule --rule transcribe-job-completion
```

### SageMaker Processing Errors

Check SageMaker console or CLI:

```bash
aws sagemaker list-processing-jobs --max-results 5
```

## Cost Estimates

For 1000 files processed:

| Service | Volume | Cost |
|---------|--------|------|
| Lambda | 5 functions × 1000 invocations × 60s | $0.02 |
| Comprehend | 1000 texts × 1000 chars | $1.00 |
| Textract | 100 images | $0.15 |
| Rekognition | 100 images | $0.10 |
| Transcribe | 100 audio × 1 min | $2.40 |
| SageMaker | 1 job × 10 min × ml.m5.xlarge | $0.03 |
| S3 | Storage + requests | $0.10 |
| **Total** | | **~$3.80** |

## Cleanup

Remove all resources:

```bash
cd iac/
terraform destroy
```

This removes:
- All Lambda functions
- S3 bucket (including all uploaded data)
- IAM roles and policies
- EventBridge rules
- CloudWatch dashboard
- Glue database and crawler

**Note**: You may need to manually delete:
- Transcription jobs (auto-deleted after 90 days)
- CloudWatch log groups (if you want immediate deletion)

## Next Steps

1. **Add alarms**: Set up CloudWatch Alarms for low quality scores
2. **Optimize costs**: Adjust Lambda memory/timeout based on actual usage
3. **Add Step Functions**: Orchestrate complex workflows
4. **Integrate with Bedrock**: Use processed data with Foundation Models
5. **Add data lake**: Store processed results in AWS Lake Formation

## Support

For issues or questions:
- Check CloudWatch Logs for detailed error messages
- Review AWS service limits in your account
- Ensure IAM permissions are correctly configured
- Verify S3 event notifications are active

