# 01_1.3 Data Validation & Processing

This module provisions the infrastructure and helpers for the customer feedback data-quality workflow. It includes:

- An S3 bucket seeded with sample feedback data (`sample-data/customer_feedback.csv`).
- AWS Glue cataloging via crawler + IAM role to support ruleset evaluations.
- A custom text-validation Lambda triggered by S3 object creation events.
- A CloudWatch dashboard that surfaces Lambda quality scores and Glue DQ pass rates.
- Utility scripts for managing Glue Data Quality rulesets.

## Purpose & Use Cases

### Primary Objective

This project demonstrates **automated data quality validation and processing** for customer feedback data, ensuring that only high-quality, validated data flows into downstream systems (like GenAI applications, analytics, or ML models).

### Business Problems It Solves

#### 1. Data Quality Assurance
- **Problem**: Customer feedback data from various sources is often incomplete, inconsistent, or low-quality
- **Solution**: Automated validation catches issues immediately before they corrupt your data pipeline
- **Impact**: Prevents "garbage in, garbage out" scenarios in AI/ML models

#### 2. Early Detection of Bad Data
- **Problem**: Discovering data quality issues after processing wastes resources and time
- **Solution**: Real-time Lambda validation provides instant feedback on uploaded files
- **Impact**: Failed validations can trigger alerts or prevent downstream processing

#### 3. Compliance & Data Governance
- **Problem**: Need to ensure data meets organizational standards and regulations
- **Solution**: Enforces rules like required fields, proper formatting, profanity filtering
- **Impact**: Maintains data integrity and regulatory compliance

#### 4. Monitoring Data Health Over Time
- **Problem**: Data quality can degrade without visibility into trends
- **Solution**: CloudWatch dashboard tracks quality metrics and pass rates
- **Impact**: Proactive identification of systemic data quality issues

### Real-World Applications

- **E-Commerce**: Validates customer product reviews before displaying on website
- **Customer Support**: Ensures feedback tickets have required information before routing
- **GenAI/ML Pipelines**: Validates training data quality before fine-tuning models
- **Analytics**: Ensures data completeness and consistency for accurate reporting

### Dual-Layer Validation Strategy

**Layer 1: Real-Time (Lambda)**
- Immediate validation on upload
- Lightweight heuristic checks (min length, sentiment, structure, profanity)
- Fast feedback loop
- Good for: Individual file quality

**Layer 2: Batch (Glue DQ)**
- Comprehensive dataset validation
- Statistical & relational checks using DQDL
- Cross-record validation
- Good for: Overall dataset health

## Architecture & Data Flow

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INFRASTRUCTURE LAYER (Terraform)                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────┐
│  S3 Bucket   │      │    Lambda    │      │  Glue Catalog│      │CloudWatch│
│  + Events    │      │   Function   │      │  + Crawler   │      │ Dashboard│
└──────────────┘      └──────────────┘      └──────────────┘      └──────────┘
```

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STEP 1: DATA INGESTION                                │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │   User/Application   │
                    │   Uploads File       │
                    │   (.txt/.json/.csv)  │
                    └──────────┬───────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────┐
        │   S3 Bucket: customer-feedback-analysis  │
        │   Path: raw-data/                        │
        │   Event: ObjectCreated:*                 │
        └──────────┬───────────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
    ▼                             ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 2A: REAL-TIME VALIDATION (Lambda Path)               │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────┐
│  Lambda Function:      │
│  TextValidationFunction│
└───────────┬────────────┘
            │
            │  ┌─────────────────────────────┐
            ├─►│ 1. Check File Type          │
            │  │    (.txt or .json only)     │
            │  └─────────────────────────────┘
            │
            │  ┌─────────────────────────────┐
            ├─►│ 2. Load Content from S3     │
            │  │    Extract text from file   │
            │  └─────────────────────────────┘
            │
            │  ┌─────────────────────────────┐
            ├─►│ 3. Apply Heuristic Checks:  │
            │  │    ✓ Min length (≥10 chars) │
            │  │    ✓ Product reference      │
            │  │    ✓ Opinion keywords       │
            │  │    ✓ No profanity           │
            │  │    ✓ Has structure (periods)│
            │  └─────────────────────────────┘
            │
            │  ┌─────────────────────────────┐
            ├─►│ 4. Calculate Quality Score  │
            │  │    Score = passed/total     │
            │  │    Example: 4/5 = 0.8       │
            │  └─────────────────────────────┘
            │
            └──────┬──────────────┬───────────
                   │              │
                   ▼              ▼
        ┌──────────────┐   ┌─────────────────┐
        │ CloudWatch   │   │  S3: validation- │
        │ Metric:      │   │      results/    │
        │ QualityScore │   │  file_result.json│
        └──────┬───────┘   └─────────────────┘
               │
               ▼
        ┌──────────────────────┐
        │  CloudWatch Logs:    │
        │  /aws/lambda/        │
        │  TextValidation...   │
        └──────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                  STEP 2B: BATCH VALIDATION (Glue Path)                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────┐
│  Glue Crawler:         │
│  customer_feedback_    │
│  crawler               │
└───────────┬────────────┘
            │  (Manual/Scheduled Trigger)
            │
            │  ┌─────────────────────────────┐
            ├─►│ 1. Scan S3 raw-data/        │
            │  │    Discover files & schema  │
            │  └─────────────────────────────┘
            │
            │  ┌─────────────────────────────┐
            ├─►│ 2. Infer Data Types         │
            │  │    customer_id, feedback,   │
            │  │    sentiment, timestamp     │
            │  └─────────────────────────────┘
            │
            │  ┌─────────────────────────────┐
            └─►│ 3. Update Glue Catalog      │
               │    Database: customer_      │
               │    feedback_db              │
               └──────────────┬──────────────┘
                              │
                              ▼
            ┌─────────────────────────────────┐
            │  Glue Data Quality Evaluator    │
            │  Ruleset: customer_reviews_     │
            │           ruleset               │
            └────────────┬────────────────────┘
                         │
                         │  ┌─────────────────────────────┐
                         ├─►│ Apply DQDL Rules:           │
                         │  │  • IsComplete checks        │
                         │  │  • ColumnLength validation  │
                         │  │  • ColumnValues constraints │
                         │  │  • Pattern matching         │
                         │  │  • RowCount validation      │
                         │  └─────────────────────────────┘
                         │
                         │  ┌─────────────────────────────┐
                         └─►│ Calculate Pass Rate         │
                            │  PassRate = rules_passed/   │
                            │             total_rules     │
                            └────────────┬────────────────┘
                                         │
                                         ▼
                            ┌────────────────────────────┐
                            │  CloudWatch Metric:        │
                            │  RulesetPassRate           │
                            │  Namespace: CustomerFeedback│
                            │            /DataQuality    │
                            └────────────┬───────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      STEP 3: UNIFIED MONITORING                              │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌────────────────────────────┐
                            │  CloudWatch Dashboard:     │
                            │  CustomerFeedbackQuality   │
                            └────────┬───────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
        ┌───────────────────┐             ┌──────────────────┐
        │  Widget 1:        │             │  Widget 2:       │
        │  Lambda Quality   │             │  Glue DQ Pass    │
        │  Score Trends     │             │  Rate Trends     │
        │  (Real-time)      │             │  (Batch)         │
        └───────────────────┘             └──────────────────┘

                    ┌────────────────────────────┐
                    │  Unified Quality View      │
                    │  • Real-time file quality  │
                    │  • Historical dataset health│
                    │  • Alerts on thresholds    │
                    └────────────────────────────┘
```

### Component Interaction Map

```
┌──────────────┐
│  Terraform   │  Provisions & Configures All Resources
└──────┬───────┘
       │
       ├──► S3 Bucket (storage + event source)
       │    └──► S3 Event Notification ──► Lambda Function
       │
       ├──► Lambda Function (real-time validation)
       │    ├──► IAM Role (permissions)
       │    ├──► S3 (read/write)
       │    └──► CloudWatch (metrics + logs)
       │
       ├──► Glue Crawler (schema discovery)
       │    ├──► IAM Role (permissions)
       │    ├──► S3 (read)
       │    └──► Glue Catalog Database
       │
       ├──► Glue Data Quality (ruleset evaluation)
       │    ├──► Ruleset (DQDL rules)
       │    ├──► Glue Catalog (table metadata)
       │    └──► CloudWatch (metrics)
       │
       └──► CloudWatch Dashboard (observability)
            ├──► Lambda Metrics
            └──► Glue DQ Metrics
```

### Sequential Processing Steps

**Phase 1: Infrastructure Setup (One-time)**
1. Run `terraform apply` to provision all resources
2. Run `create_glue_data_quality_ruleset.py` to register DQDL rules
3. Verify dashboard creation in CloudWatch

**Phase 2: Real-Time Processing (Per File Upload)**
1. File uploaded to `s3://bucket/raw-data/`
2. S3 triggers Lambda within milliseconds
3. Lambda validates file (5 heuristic checks)
4. Quality score published to CloudWatch
5. Validation results stored in `validation-results/`

**Phase 3: Batch Processing (Scheduled/Manual)**
1. Glue Crawler runs to discover schema
2. Catalog updated with table metadata
3. Glue DQ evaluator runs DQDL rules
4. Pass rate published to CloudWatch
5. Dashboard reflects comprehensive health

**Phase 4: Continuous Monitoring**
1. Dashboard displays both real-time and batch metrics
2. CloudWatch Alarms can trigger on low quality scores
3. Validation results available for audit/analysis

### Learning Objectives

This project teaches key AWS patterns for production GenAI systems:

- **AWS Service Integration**: S3, Lambda, Glue, CloudWatch, IAM
- **Event-Driven Architecture**: Serverless, scalable data processing
- **Data Quality Best Practices**: Multi-layer validation strategies
- **Infrastructure as Code**: Terraform for reproducible deployments
- **Observability**: Unified monitoring across validation layers

## Repository Layout

```
01_1.3_data_validate_processing/
├── sample-data/                     # CSVs uploaded to s3://<bucket>/raw-data/
├── lambda_custom_text_validation.py # Lambda handler used by IaC
├── create_glue_data_quality_ruleset.py
└── iac/
    ├── main.tf        # S3, Glue, IAM resources
    ├── lambda.tf      # Lambda package, role, trigger
    └── monitoring.tf  # CloudWatch dashboard
```

## Architecture Overview

1. **Raw Data Landing (S3)**  
   - Reviews are uploaded to `s3://customer-feedback-analysis-<initials>/raw-data/`.  
   - Terraform seeds the bucket with `customer_feedback.csv` and enforces public-access blocks.

2. **Event-Driven Validation (Lambda + CloudWatch)**  
   - An S3 `ObjectCreated` notification invokes `TextValidationFunction`.  
   - The Lambda reads the new object, applies heuristic checks, emits a `QualityScore` metric, and writes a JSON result under `validation-results/`.  
   - CloudWatch Logs capture execution details while the dashboard visualizes the quality scores.

3. **Catalog & Data Quality (Glue)**  
   - Glue crawler discovers table metadata under the `raw-data/` prefix and stores it in `customer_feedback_db`.  
   - The Glue Data Quality ruleset (`customer_reviews_ruleset`) can be evaluated against that table to track pass rates.

4. **Observability (CloudWatch Dashboard)**  
   - Dashboard widgets display both Lambda `QualityScore` trends and Glue `RulesetPassRate`, enabling a unified health view across streaming and batch quality checks.

This architecture ensures new feedback data is validated immediately while longer-running Glue DQ jobs and the dashboard provide historical visibility.

## Prerequisites

- Terraform ≥ 1.6 with AWS credentials configured (profile or environment variables).
- Python 3.11 virtual environment (`python3 -m venv .venv && source .venv/bin/activate`).
- Dependencies installed: `pip install -r requirements.txt` (provides `boto3`, `awsglue`).

## Deploying with Terraform

1. Change into the IaC directory:
   ```bash
   cd 01_1.3_data_validate_processing/iac
   terraform init
   ```
2. Review changes and deploy:
   ```bash
   terraform plan
   terraform apply
   ```

The plan:
- Creates (or reuses) `customer-feedback-analysis-<initials>` S3 bucket.
- Uploads `raw-data/customer_feedback.csv` using Terraform’s `filemd5()` to force updates when the CSV changes.
- Sets up Glue database + crawler referencing `raw-data/`.
- Packages and deploys the Lambda function (using `archive_file` to zip `lambda_custom_text_validation.py`).
- Adds CloudWatch dashboard widgets for Lambda quality scores and Glue DQ ruleset pass rate.

## Lambda Text Validation

`lambda_custom_text_validation.py`:
- Only processes `.txt` or `.json` objects placed under `raw-data/`.
- Validates textual heuristics (minimum length, product reference, opinion keywords, profanity blacklist, simple structure).
- Publishes a `QualityScore` metric into `CustomerFeedback/TextQuality`.
- Stores per-file validation results under `validation-results/` in JSON form.

Environment variables can override regex patterns (`PROFANITY_REGEX`, `PRODUCT_REGEX`, `OPINION_REGEX`) and metric names (`CLOUDWATCH_NAMESPACE`, `METRIC_SOURCE`).

## Glue Data Quality Ruleset

Use `create_glue_data_quality_ruleset.py` when you need to (re)register the `customer_reviews_ruleset`:

```bash
source .venv/bin/activate
python 01_1.3_data_validate_processing/create_glue_data_quality_ruleset.py --region us-east-1
```

This script creates completeness, pattern, and length-distribution rules for reviews and tags the ruleset with `Project=CustomerFeedbackAnalysis`.

## Validating the Workflow

1. Upload a new review file (txt/json) to `s3://customer-feedback-analysis-<initials>/raw-data/`.
2. Confirm:
   - Lambda runs (`validation-results/` object + CloudWatch Logs entry).
   - `QualityScore` metric updates (visible on the dashboard).
   - Glue crawler runs (manually trigger or schedule) to refresh the catalog.
3. Run Glue DQ evaluation referencing `customer_reviews_ruleset` if needed; the dashboard widget reflects the pass rate metric `CustomerFeedback/DataQuality`.

## Cleanup

From `iac/` run:

```bash
terraform destroy
```

This removes the bucket (including uploaded data), Lambda, IAM roles, and dashboard.	Delete the `.venv` folder manually if it is no longer required.

