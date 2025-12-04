import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict

import boto3

S3_CLIENT = boto3.client("s3")
CLOUDWATCH_CLIENT = boto3.client("cloudwatch")

PROFANITY_PATTERN = os.environ.get(
    "PROFANITY_REGEX",
    r"badword1|badword2",  # Extend via Lambda env var
)

PRODUCT_PATTERN = os.environ.get(
    "PRODUCT_REGEX",
    r"product|item|purchase",
)

OPINION_PATTERN = os.environ.get(
    "OPINION_REGEX",
    r"like|love|hate|good|bad|great|terrible|excellent|poor|recommend",
)


def _is_text_review(key: str) -> bool:
    return key.endswith(".txt") or key.endswith(".json")


def _load_review_text(bucket: str, key: str) -> str:
    response = S3_CLIENT.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")

    if key.endswith(".json"):
        review = json.loads(content)
        return review.get("review_text", "")

    return content


def _validate_text(text: str) -> Dict[str, bool]:
    """Apply simple heuristics to evaluate text quality."""
    if text is None:
        text = ""

    return {
        "min_length": len(text) >= 10,
        "has_product_reference": bool(re.search(PRODUCT_PATTERN, text, re.IGNORECASE)),
        "has_opinion": bool(re.search(OPINION_PATTERN, text, re.IGNORECASE)),
        "no_profanity": not bool(re.search(PROFANITY_PATTERN, text, re.IGNORECASE)),
        "has_structure": text.count(".") >= 1,
    }


def _put_quality_metric(score: float) -> None:
    CLOUDWATCH_CLIENT.put_metric_data(
        Namespace=os.environ.get("CLOUDWATCH_NAMESPACE", "CustomerFeedback/TextQuality"),
        MetricData=[
            {
                "MetricName": "QualityScore",
                "Value": score,
                "Unit": "None",
                "Dimensions": [
                    {"Name": "Source", "Value": os.environ.get("METRIC_SOURCE", "TextReviews")}
                ],
            }
        ],
    )


def _store_validation_result(bucket: str, key: str, payload: Dict[str, Any]) -> None:
    validation_key = (
        key.replace("raw-data", "validation-results")
        .replace(".txt", ".json")
        .replace(".json", "_validation.json")
    )

    S3_CLIENT.put_object(
        Bucket=bucket,
        Key=validation_key,
        Body=json.dumps(payload),
        ContentType="application/json",
    )


def lambda_handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    if not _is_text_review(key):
        return {"statusCode": 200, "body": json.dumps("Not a text review file")}

    try:
        text = _load_review_text(bucket, key)
        checks = _validate_text(text)
        passed_checks = sum(1 for result in checks.values() if result)
        total_checks = len(checks)
        quality_score = passed_checks / total_checks if total_checks else 0.0

        validation_results = {
            "file_name": key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "quality_score": quality_score,
        }

        _put_quality_metric(quality_score)
        _store_validation_result(bucket, key, validation_results)

        return {"statusCode": 200, "body": json.dumps(validation_results)}

    except Exception as exc:  # pragma: no cover - runtime diagnostic
        print(f"Error processing {key}: {exc}")
        return {"statusCode": 500, "body": json.dumps(f"Error: {exc}")}

