import pandas as pd
import numpy as np
import argparse
import os
import json

def process_survey_data(input_path, output_path):
    """Process survey data and generate natural language summaries"""
    # Read the survey data
    csv_file = os.path.join(input_path, "surveys.csv")
    df = pd.read_csv(csv_file)
    
    print(f"Loaded {len(df)} survey responses")
    
    # Basic data cleaning
    df = df.dropna(subset=['customer_id', 'survey_date'])  # Drop rows with missing key fields
    print(f"After cleaning: {len(df)} survey responses")
    
    # Convert categorical ratings to numerical
    rating_map = {
        'Very Dissatisfied': 1,
        'Dissatisfied': 2,
        'Neutral': 3,
        'Satisfied': 4,
        'Very Satisfied': 5
    }
    
    for col in df.columns:
        if 'rating' in col.lower() or 'satisfaction' in col.lower():
            # Try to map if string, otherwise leave as is
            if df[col].dtype == 'object':
                df[col] = df[col].map(rating_map).fillna(df[col])
    
    # Calculate summary statistics
    summary_stats = {
        'total_surveys': int(len(df)),
        'avg_satisfaction': float(df['overall_satisfaction'].mean()) if 'overall_satisfaction' in df.columns else 0,
        'sentiment_distribution': df['overall_satisfaction'].value_counts().to_dict() if 'overall_satisfaction' in df.columns else {},
        'top_issues': df['improvement_area'].value_counts().head(3).to_dict() if 'improvement_area' in df.columns else {}
    }
    
    # Convert numpy types to Python types for JSON serialization
    summary_stats['sentiment_distribution'] = {
        str(k): int(v) for k, v in summary_stats['sentiment_distribution'].items()
    }
    summary_stats['top_issues'] = {
        str(k): int(v) for k, v in summary_stats['top_issues'].items()
    }
    
    # Generate natural language summaries for each survey
    summaries = []
    for idx, row in df.iterrows():
        summary = {
            'customer_id': str(row['customer_id']),
            'survey_date': str(row['survey_date']),
            'summary_text': generate_summary(row),
            'ratings': {
                col: float(row[col]) if pd.notna(row[col]) else None
                for col in df.columns 
                if ('rating' in col.lower() or 'satisfaction' in col.lower()) and pd.notna(row.get(col))
            },
            'comments': str(row.get('comments', '')) if pd.notna(row.get('comments')) else ''
        }
        summaries.append(summary)
    
    # Save the processed data
    with open(os.path.join(output_path, 'survey_summaries.json'), 'w') as f:
        json.dump(summaries, f, indent=2)
    
    with open(os.path.join(output_path, 'survey_statistics.json'), 'w') as f:
        json.dump(summary_stats, f, indent=2)
    
    print(f"Saved {len(summaries)} survey summaries")
    print(f"Summary statistics: {summary_stats}")

def generate_summary(row):
    """Generate a natural language summary of a survey response"""
    satisfaction_level = "satisfied"
    
    if 'overall_satisfaction' in row and pd.notna(row['overall_satisfaction']):
        score = float(row['overall_satisfaction'])
        satisfaction_level = "satisfied" if score >= 4 else \
                            "neutral" if score == 3 else "dissatisfied"
    
    summary = f"Customer {row['customer_id']} was {satisfaction_level} overall with their experience. "
    
    # Add details about specific ratings
    if 'product_rating' in row and pd.notna(row['product_rating']):
        summary += f"They rated the product {row['product_rating']}/5. "
    
    if 'service_rating' in row and pd.notna(row['service_rating']):
        summary += f"They rated the customer service {row['service_rating']}/5. "
    
    # Add improvement area if available
    if 'improvement_area' in row and pd.notna(row['improvement_area']):
        summary += f"They suggested improvements in the area of {row['improvement_area']}. "
    
    # Add comments if available
    if 'comments' in row and pd.notna(row['comments']) and len(str(row['comments'])) > 0:
        summary += f"Their comments: '{row['comments']}'"
    
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", type=str, default="/opt/ml/processing/input")
    parser.add_argument("--output-path", type=str, default="/opt/ml/processing/output")
    args = parser.parse_args()
    
    process_survey_data(args.input_path, args.output_path)
    print("Survey processing completed successfully")

