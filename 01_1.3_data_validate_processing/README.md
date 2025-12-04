# 01_1.3 Data Validation & Processing

Automated data quality validation pipeline for customer feedback using AWS serverless services. Demonstrates dual-layer validation (real-time + batch) with unified monitoring for GenAI/ML data pipelines.

## Purpose

Ensures high-quality, validated data flows into downstream systems by:
- **Preventing bad data** from corrupting AI/ML models ("garbage in, garbage out")
- **Early detection** with instant feedback on uploaded files
- **Compliance enforcement** through automated rules and profanity filtering
- **Continuous monitoring** of data health trends via CloudWatch dashboard

### Use Cases
- **E-Commerce**: Validate product reviews before publication
- **Customer Support**: Ensure complete feedback tickets before routing
- **GenAI/ML**: Quality-gate training data before model fine-tuning
- **Analytics**: Maintain data consistency for accurate reporting

## Architecture

### Components
```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────┐
│  S3 Bucket   │────► │    Lambda    │────► │CloudWatch    │◄────┤  Glue    │
│  + Events    │      │  Validation  │      │  Dashboard   │     │ Crawler  │
└──────────────┘      └──────────────┘      └──────────────┘     │   + DQ   │
                                                                   └──────────┘
```

### Dual-Layer Validation

**Layer 1: Real-Time (Lambda)**
- Triggered by S3 `ObjectCreated` events on `raw-data/` prefix
- Validates: min length, product reference, opinion keywords, profanity, structure
- Outputs: Quality score (0-1) → CloudWatch + JSON result → `validation-results/`

**Layer 2: Batch (Glue Data Quality)**
- Crawler discovers schema from S3 files → Glue Catalog
- DQDL ruleset evaluates: completeness, patterns, column constraints, row counts
- Outputs: Pass rate → CloudWatch metric `RulesetPassRate`

**Unified Monitoring**: CloudWatch Dashboard displays both real-time and batch metrics

### Data Flow

```
User Upload (.txt/.json/.csv)
    │
    ▼
S3: raw-data/
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
Lambda (real-time)  Glue Crawler    CloudWatch
    │                  │              Dashboard
    │                  ▼                  │
    │              Glue DQ                │
    │              Evaluator              │
    │                  │                  │
    ├──► CloudWatch ◄──┤                  │
    │    Metrics        │                  │
    │                   │                  │
    └───────────────────┴──────────────────┘
              Unified Quality View
```

## Repository Layout

```
01_1.3_data_validate_processing/
├── sample-data/
│   └── customer_feedback.csv           # Sample data (uploaded to S3 by Terraform)
├── lambda_custom_text_validation.py    # Lambda handler (5 heuristic checks)
├── create_glue_data_quality_ruleset.py # Script to register DQDL rules
└── iac/
    ├── main.tf                         # S3, Glue, IAM resources
    ├── lambda.tf                       # Lambda package, role, trigger
    └── monitoring.tf                   # CloudWatch dashboard
```

## Quick Start

### Prerequisites
- Terraform ≥ 1.6 with AWS credentials configured
- Python 3.11+ with boto3 installed

### Deploy Infrastructure

```bash
cd 01_1.3_data_validate_processing/iac
terraform init
terraform plan
terraform apply
```

This provisions:
- S3 bucket `customer-feedback-analysis-<initials>` with sample CSV
- Lambda function `TextValidationFunction` with S3 event trigger
- Glue database `customer_feedback_db` + crawler `customer_feedback_crawler`
- CloudWatch dashboard `CustomerFeedbackQuality`

### Register Glue Data Quality Rules

```bash
python create_glue_data_quality_ruleset.py --region us-east-1
```

Creates ruleset `customer_reviews_ruleset` with DQDL rules:
- `IsComplete` checks for required fields
- `ColumnLength` validation (feedback ≥ 10 chars)
- `ColumnValues` constraints (sentiment must be Positive/Neutral/Negative)
- Pattern matching for timestamp format

### Test the Workflow

1. Upload a file to trigger validation:
```bash
aws s3 cp review.txt s3://customer-feedback-analysis-<initials>/raw-data/
```

2. Check Lambda execution:
   - View logs: `/aws/lambda/TextValidationFunction` in CloudWatch
   - Find results: `s3://bucket/validation-results/review_validation.json`

3. Run Glue Crawler (manual or scheduled):
```bash
aws glue start-crawler --name customer_feedback_crawler
```

4. View metrics on CloudWatch Dashboard: `CustomerFeedbackQuality`

## Lambda Validation Details

**File Processing** (`lambda_custom_text_validation.py`):
- Accepts: `.txt` and `.json` files in `raw-data/` prefix only
- Checks: 5 heuristic validations
- Score: `passed_checks / total_checks` (e.g., 4/5 = 0.8)
- Outputs:
  - CloudWatch metric: `CustomerFeedback/TextQuality::QualityScore`
  - S3 JSON: Per-file validation results with timestamp

**Environment Variables**:
- `PROFANITY_REGEX`: Custom profanity pattern (default: `badword1|badword2`)
- `PRODUCT_REGEX`: Product reference pattern
- `OPINION_REGEX`: Opinion keyword pattern
- `CLOUDWATCH_NAMESPACE`: Metric namespace
- `METRIC_SOURCE`: Metric dimension value

## Glue Data Quality Details

**DQDL Rules** (registered via `create_glue_data_quality_ruleset.py`):

```
IsComplete "customer_id"
IsComplete "feedback_text"
IsComplete "sentiment"
IsComplete "timestamp"
ColumnLength "feedback_text" >= 10
ColumnValues "sentiment" in ["Positive", "Neutral", "Negative"]
ColumnValues "timestamp" matches "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
RowCount > 0
```

**Evaluation**:
```bash
aws glue start-data-quality-ruleset-evaluation \
  --ruleset-name customer_reviews_ruleset \
  --database customer_feedback_db \
  --table <discovered_table_name>
```

Publishes `CustomerFeedback/DataQuality::RulesetPassRate` metric to CloudWatch.

## Multimodal Data Processing (Extended Pipeline)

This project supports processing **4 types of data modalities** beyond basic text validation:

### 1. Text Review Processing (Amazon Comprehend)

**Lambda Function**: `TextProcessingFunction`

Processes validated text reviews (quality score ≥ 0.7) with NLP:
- **Entity Extraction**: Identifies people, organizations, locations, products
- **Sentiment Analysis**: Detects emotional tone (POSITIVE, NEGATIVE, NEUTRAL, MIXED)
- **Key Phrases**: Extracts important topics and themes

**Trigger**: S3 event on `validation-results/*_validation.json` files

**Output**: `processed-data/<filename>_processed.json` with enriched insights

**Example**:
```bash
aws s3 cp sample-data/review1.json s3://<bucket>/raw-data/
# Automatically: Validates → Processes with Comprehend → Saves enriched data
```

### 2. Image Processing (Textract + Rekognition)

**Lambda Function**: `ImageProcessingFunction`

Extracts text and visual insights from product images:
- **OCR (Textract)**: Extracts text from labels, packaging, documents
- **Label Detection (Rekognition)**: Identifies objects, scenes, activities
- **Text Detection (Rekognition)**: Backup text extraction with confidence scores

**Trigger**: S3 event on `raw-data/images/*.{jpg,jpeg,png}` files

**Output**: `processed-data/images/<filename>_processed.json`

**Use Cases**: Product damage assessment, barcode/serial number extraction, packaging compliance

**Example**:
```bash
aws s3 cp product_label.jpg s3://<bucket>/raw-data/images/
```

### 3. Audio Processing (Transcribe + Comprehend)

**Lambda Functions**: 
- `AudioProcessingFunction` (starts transcription)
- `TranscriptionCompletionFunction` (processes completed transcription)

Converts customer service calls to text with sentiment analysis:
- **Speech-to-Text (Transcribe)**: Transcribes audio to text
- **Speaker Diarization**: Identifies who said what (customer vs agent)
- **Sentiment Analysis (Comprehend)**: Analyzes conversation tone
- **Key Phrase Extraction**: Identifies main topics discussed

**Trigger**: S3 event on `raw-data/audio/*.{mp3,wav,flac}` files

**Flow**: Upload → Start Transcribe Job → EventBridge triggers completion → Process with Comprehend

**Output**: `processed-data/audio/<job-name>_processed.json`

**Example**:
```bash
aws s3 cp customer_call.mp3 s3://<bucket>/raw-data/audio/
```

### 4. Survey Processing (SageMaker Processing)

**Script**: `sagemaker_survey_processing.py`

Batch processes structured survey data at scale:
- **Data Normalization**: Converts categorical ratings to numerical scores
- **Statistical Aggregation**: Calculates averages, distributions, top issues
- **Natural Language Summaries**: Generates text summaries from structured data

**Trigger**: Manual execution via `run_sagemaker_survey_job.py`

**Output**: 
- `processed-data/surveys/survey_summaries.json` (per-response summaries)
- `processed-data/surveys/survey_statistics.json` (aggregate statistics)

**Example**:
```bash
python run_sagemaker_survey_job.py --bucket <bucket-name> --region us-east-1
```

### Multimodal Pipeline Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                       │
└──────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
      [Text Files]      [Images]         [Audio Files]
      [Survey CSV]
            │                 │                 │
            ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────────────┐
│               VALIDATION & PROCESSING LAYER                   │
└──────────────────────────────────────────────────────────────┘
            │                 │                 │
    TextValidation    ImageProcessing   AudioProcessing
    → Comprehend      → Textract        → Transcribe
                      → Rekognition     → Comprehend
            │                 │                 │
            └─────────────────┼─────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    PROCESSED DATA STORE                       │
│  • Entities & Sentiment                                       │
│  • Visual Labels & Text                                       │
│  • Transcripts & Speaker Labels                               │
│  • Survey Summaries & Stats                                   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  [Ready for Foundation Models]
```

### AWS Services Used

| Service | Purpose | Cost Consideration |
|---------|---------|-------------------|
| **Amazon Comprehend** | NLP (entities, sentiment, key phrases) | $0.0001 per unit (100 chars) |
| **Amazon Textract** | OCR from images | $1.50 per 1000 pages |
| **Amazon Rekognition** | Image labels & text detection | $1.00 per 1000 images |
| **Amazon Transcribe** | Speech-to-text | $0.024 per minute |
| **SageMaker Processing** | Batch data transformation | Instance hours |

### Sample Data

See `sample-data/SAMPLE_DATA_README.md` for:
- Sample JSON reviews (3 files with different sentiments)
- Sample survey CSV (10 responses)
- Instructions for creating test images and audio files

## Monitoring

**CloudWatch Dashboard Widgets**:
1. **Lambda Quality Score Trends** (real-time per-file metrics)
2. **Glue DQ Pass Rate** (batch dataset-level metrics)

Set up alarms to trigger notifications when quality scores drop below thresholds.

## Cleanup

```bash
cd iac/
terraform destroy
```

Removes: S3 bucket (including data), Lambda function, IAM roles, Glue resources, and dashboard.

## Learning Objectives

- **Event-Driven Architecture**: S3 events trigger serverless Lambda processing
- **Multi-Layer Validation**: Real-time heuristics + batch statistical checks
- **AWS Service Integration**: S3, Lambda, Glue, CloudWatch, IAM
- **Infrastructure as Code**: Reproducible Terraform deployments
- **Production GenAI Patterns**: Data quality gates for ML pipelines
