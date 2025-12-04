# Quick Start Guide - Multimodal Data Processing

## 🚀 5-Minute Deployment

### 1. Deploy Infrastructure
```bash
cd 01_1.3_data_validate_processing/iac
terraform init
terraform apply -auto-approve
```

### 2. Get Bucket Name
```bash
BUCKET=$(terraform output -raw project_bucket_name 2>/dev/null || echo "customer-feedback-analysis-ars")
echo "Using bucket: $BUCKET"
```

### 3. Register Data Quality Rules
```bash
cd ..
python create_glue_data_quality_ruleset.py --region us-east-1
```

## ✅ Test Each Pipeline

### Text Processing
```bash
# Upload sample review
aws s3 cp sample-data/review1.json s3://$BUCKET/raw-data/

# Wait 5 seconds
sleep 5

# Check processed results
aws s3 cp s3://$BUCKET/processed-data/review1_processed.json - | jq .sentiment
```

### Image Processing
```bash
# Create test image (requires ImageMagick)
convert -size 800x600 xc:white \
  -font Arial -pointsize 36 -fill black \
  -gravity center -annotate +0+0 "Product: TEST\nPrice: $99" \
  test.png

# Upload
aws s3 cp test.png s3://$BUCKET/raw-data/images/

# Check results (wait 10 seconds)
sleep 10
aws s3 cp s3://$BUCKET/processed-data/images/test_processed.json - | jq .extracted_text
```

### Audio Processing
```bash
# Create TTS audio
aws polly synthesize-speech \
  --output-format mp3 \
  --voice-id Joanna \
  --text "Hello, this is a test customer service call." \
  test.mp3

# Upload
aws s3 cp test.mp3 s3://$BUCKET/raw-data/audio/

# Check transcription (wait 60 seconds for job completion)
sleep 60
aws s3 ls s3://$BUCKET/processed-data/audio/
```

### Survey Processing
```bash
# Upload survey data
aws s3 cp sample-data/surveys.csv s3://$BUCKET/raw-data/

# Run SageMaker job (requires SageMaker role)
python run_sagemaker_survey_job.py --bucket $BUCKET
```

## 📊 Monitor

```bash
# View logs
aws logs tail /aws/lambda/TextProcessingFunction --follow

# Check dashboard
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=CustomerFeedbackQuality"
```

## 🧹 Cleanup

```bash
cd iac/
terraform destroy -auto-approve
```

## 📚 Full Documentation

- **README.md** - Complete project documentation
- **MULTIMODAL_DEPLOYMENT_GUIDE.md** - Detailed deployment guide
- **PROJECT_SUMMARY.md** - Architecture and learning outcomes
- **sample-data/SAMPLE_DATA_README.md** - Sample data usage

## 🆘 Troubleshooting

**Lambda errors?**
```bash
aws logs tail /aws/lambda/<FunctionName> --since 10m
```

**No processed data?**
- Check quality score: Must be ≥ 0.7 for text processing
- Check CloudWatch Logs for errors
- Verify IAM permissions

**Transcribe not working?**
- Check audio format: MP3, WAV, or FLAC
- Ensure audio is at least 0.5 seconds
- Check EventBridge rule is active

## 💰 Costs

**Estimate for testing (10 files each)**:
- Lambda: $0.00 (free tier)
- Comprehend: $0.01
- Textract: $0.02
- Rekognition: $0.01
- Transcribe: $0.24
- **Total: ~$0.28**

## 🎯 Success Criteria

✅ All 5 Lambda functions deployed  
✅ S3 bucket notifications configured  
✅ Sample text processed with sentiment  
✅ CloudWatch dashboard visible  
✅ Costs under $1 for testing  

**Next**: See `MULTIMODAL_DEPLOYMENT_GUIDE.md` for advanced testing and production setup.

