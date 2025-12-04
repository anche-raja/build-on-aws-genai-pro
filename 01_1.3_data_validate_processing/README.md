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
