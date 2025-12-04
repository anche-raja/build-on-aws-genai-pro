"""
Utility script to create a Glue Data Quality ruleset for customer reviews.

Usage:
    python create_glue_data_quality_ruleset.py --region us-east-1

Prerequisites:
  - AWS credentials configured (env vars, ~/.aws/credentials, or IAM role)
  - boto3 and awsglue Python packages installed
  - The Glue Data Catalog database/table already exists or is discoverable
"""

import argparse
import sys

import boto3
from awsglue.data_quality import DataQualityRule


def build_ruleset_string() -> str:
    """Compose the Glue Data Quality rules for customer reviews."""
    rules = [
        # Completeness checks
        DataQualityRule.is_complete("review_text"),
        DataQualityRule.is_complete("product_id"),
        DataQualityRule.is_complete("customer_id"),
        DataQualityRule.is_complete("rating"),
        DataQualityRule.is_complete("review_date"),

        # Valid value checks
        DataQualityRule.column_values_match_pattern("review_text", ".{10,}"),
        DataQualityRule.column_values_match_pattern("rating", "^[1-5]$"),

        # Consistency checks
        DataQualityRule.column_values_match_pattern("review_date", r"\d{4}-\d{2}-\d{2}"),

        # Statistical properties
        DataQualityRule.column_length_distribution_match(
            "review_text",
            min_length=10,
            max_length=5000,
        ),
    ]

    return "\n".join(str(rule) for rule in rules)


def create_ruleset(region: str) -> None:
    """Create the Glue Data Quality ruleset in the target AWS region."""
    glue_client = boto3.client("glue", region_name=region)
    response = glue_client.create_data_quality_ruleset(
        Name="customer_reviews_ruleset",
        Description="Data quality rules for customer reviews",
        Ruleset=build_ruleset_string(),
        Tags={"Project": "CustomerFeedbackAnalysis"},
    )

    print(f"Created ruleset: {response['Name']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Glue Data Quality ruleset.")
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region where Glue is provisioned (default: us-east-1)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        create_ruleset(region=args.region)
    except Exception as exc:  # pragma: no cover - utility script
        print(f"Failed to create ruleset: {exc}", file=sys.stderr)
        sys.exit(1)

