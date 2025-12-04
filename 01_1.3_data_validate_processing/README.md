# 01_1.3 Data Validation & Processing

This module provisions the infrastructure and helpers for the customer feedback data-quality workflow. It includes:

- An S3 bucket seeded with sample feedback data (`sample-data/customer_feedback.csv`).
- AWS Glue cataloging via crawler + IAM role to support ruleset evaluations.
- A custom text-validation Lambda triggered by S3 object creation events.
- A CloudWatch dashboard that surfaces Lambda quality scores and Glue DQ pass rates.
- Utility scripts for managing Glue Data Quality rulesets.

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

