import boto3
import sys

# AWS Glue Data Quality rules use DQDL (Data Quality Definition Language)
# Rules are defined as strings, not Python objects

# Define rules for customer feedback data
# Based on the actual columns: customer_id, feedback_text, sentiment, timestamp
rules = """Rules = [
    IsComplete "customer_id",
    IsComplete "feedback_text",
    IsComplete "sentiment",
    IsComplete "timestamp",
    
    ColumnLength "feedback_text" >= 10,
    ColumnValues "sentiment" in ["Positive", "Neutral", "Negative"],
    ColumnValues "timestamp" matches "\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}",
    
    RowCount > 0
]"""

def create_ruleset(region='us-east-1'):
    # Create ruleset using boto3
    glue_client = boto3.client('glue', region_name=region)
    
    try:
        response = glue_client.create_data_quality_ruleset(
            Name='customer_reviews_ruleset',
            Description='Data quality rules for customer feedback',
            Ruleset=rules,
            Tags={'Project': 'CustomerFeedbackAnalysis'}
        )
        print(f"✓ Created ruleset: {response['Name']}")
        return response
    except glue_client.exceptions.AlreadyExistsException:
        print("Ruleset already exists. Updating...")
        response = glue_client.update_data_quality_ruleset(
            Name='customer_reviews_ruleset',
            Description='Data quality rules for customer feedback',
            Ruleset=rules
        )
        print(f"✓ Updated ruleset: customer_reviews_ruleset")
        return response
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Allow region override via command line
    region = sys.argv[1] if len(sys.argv) > 1 else 'us-east-1'
    
    if region.startswith('--region'):
        region = sys.argv[2] if len(sys.argv) > 2 else 'us-east-1'
    
    create_ruleset(region)
