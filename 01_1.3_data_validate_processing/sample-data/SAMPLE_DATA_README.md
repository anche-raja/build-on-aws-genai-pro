# Sample Data Files

This directory contains sample data files for testing the multimodal data processing pipeline.

## Text Reviews (JSON)

- `review1.json` - Positive review (5-star rating)
- `review2.json` - Neutral review (3-star rating)
- `review3.json` - Negative review (1-star rating)

**Usage:**
Upload these to `s3://<bucket>/raw-data/` to trigger text validation and processing.

## Customer Feedback (CSV/TXT)

- `customer_feedback.csv` - Original CSV format for basic validation
- `customer_feedback.txt` - Text format with comma-separated values

**Usage:**
Already uploaded by Terraform to `s3://<bucket>/raw-data/`.

## Surveys (CSV)

- `surveys.csv` - Survey responses with ratings and comments (10 responses)

**Usage:**
Upload to `s3://<bucket>/raw-data/` and process with SageMaker:
```bash
python run_sagemaker_survey_job.py --bucket <bucket-name> --region us-east-1
```

## Images

For image processing, you need actual image files. Here are some options:

### Option 1: Create a simple test image
Use any product image (PNG, JPG, JPEG format) and upload to `s3://<bucket>/raw-data/images/`

### Option 2: Use sample images with text
Create images with:
- Product labels/barcodes
- Packaging with text
- Product manuals
- Damaged product photos

**Suggested test images:**
1. `product_P98765_label.jpg` - Product label with barcode and text
2. `product_P98766_damage.jpg` - Photo showing product damage
3. `packaging_text.png` - Package with product information

**Upload command:**
```bash
aws s3 cp sample_image.jpg s3://<bucket>/raw-data/images/
```

**What the Lambda will extract:**
- Text from labels (via Textract)
- Product categories/objects (via Rekognition labels)
- Confidence scores for each detection

## Audio Files

For audio processing, you need actual audio files. Here are some options:

### Option 1: Text-to-Speech Sample
Use AWS Polly or any TTS service to create sample customer service call:

**Sample script:**
```
Agent: "Thank you for calling customer service, how can I help you today?"
Customer: "Hi, I'm calling about my recent order. The product arrived damaged and I need a replacement."
Agent: "I'm sorry to hear that. Let me look up your order and process a replacement right away."
Customer: "Thank you, I appreciate your help."
```

### Option 2: Record a sample call
Record a short MP3/WAV file (30-60 seconds) simulating a customer service interaction.

**Supported formats:** MP3, WAV, FLAC

**Upload command:**
```bash
aws s3 cp customer_call_001.mp3 s3://<bucket>/raw-data/audio/
```

**What the Lambda will do:**
1. Start Amazon Transcribe job (async)
2. EventBridge triggers completion Lambda when done
3. Transcription processed with Comprehend for sentiment
4. Results saved to `s3://<bucket>/processed-data/audio/`

## Testing the Complete Pipeline

### Step 1: Deploy Infrastructure
```bash
cd iac/
terraform init
terraform apply
```

### Step 2: Upload Sample Data

**Text reviews:**
```bash
aws s3 cp sample-data/review1.json s3://<bucket>/raw-data/
aws s3 cp sample-data/review2.json s3://<bucket>/raw-data/
```

**Images:**
```bash
aws s3 cp sample_image.jpg s3://<bucket>/raw-data/images/
```

**Audio:**
```bash
aws s3 cp sample_audio.mp3 s3://<bucket>/raw-data/audio/
```

**Surveys:**
```bash
aws s3 cp sample-data/surveys.csv s3://<bucket>/raw-data/
python run_sagemaker_survey_job.py --bucket <bucket-name>
```

### Step 3: Check Results

**Validation results:**
```bash
aws s3 ls s3://<bucket>/validation-results/
```

**Processed data:**
```bash
aws s3 ls s3://<bucket>/processed-data/
aws s3 ls s3://<bucket>/processed-data/images/
aws s3 ls s3://<bucket>/processed-data/audio/
aws s3 ls s3://<bucket>/processed-data/surveys/
```

**View CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/TextValidationFunction --follow
aws logs tail /aws/lambda/TextProcessingFunction --follow
aws logs tail /aws/lambda/ImageProcessingFunction --follow
aws logs tail /aws/lambda/AudioProcessingFunction --follow
```

## Data Flow

```
1. Text Review Upload
   raw-data/review1.json
   → TextValidationFunction (quality check)
   → validation-results/review1_validation.json
   → TextProcessingFunction (Comprehend)
   → processed-data/review1_processed.json

2. Image Upload
   raw-data/images/product.jpg
   → ImageProcessingFunction (Textract + Rekognition)
   → processed-data/images/product_processed.json

3. Audio Upload
   raw-data/audio/call.mp3
   → AudioProcessingFunction (start Transcribe)
   → transcriptions/call.json
   → EventBridge → TranscriptionCompletionFunction (Comprehend)
   → processed-data/audio/transcribe-xxx_processed.json

4. Survey Upload
   raw-data/surveys.csv
   → SageMaker Processing Job
   → processed-data/surveys/survey_summaries.json
   → processed-data/surveys/survey_statistics.json
```

## Notes

- Text files must pass quality validation (score ≥ 0.7) before processing
- Images should be clear with visible text for best Textract results
- Audio files should be clear speech in English for best transcription
- Survey CSV must have the expected column headers
- All processing is asynchronous and event-driven
- Check CloudWatch Logs for detailed execution information

