"""
Script to run SageMaker Processing job for survey data.
This can be executed locally or as part of a Step Functions workflow.
"""
import boto3
import sagemaker
from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput
import argparse

def run_survey_processing_job(bucket_name, region='us-east-1'):
    """
    Run a SageMaker Processing job to process survey data.
    
    Args:
        bucket_name: Name of the S3 bucket containing the data
        region: AWS region to run the job in
    """
    # Initialize SageMaker session
    boto_session = boto3.Session(region_name=region)
    sagemaker_session = sagemaker.Session(boto_session=boto_session)
    
    # Get the execution role
    # In production, you'd create a specific role for SageMaker
    sts_client = boto3.client('sts', region_name=region)
    account_id = sts_client.get_caller_identity()['Account']
    role = f"arn:aws:iam::{account_id}:role/SageMakerExecutionRole"
    
    print(f"Using role: {role}")
    print(f"Processing data from: s3://{bucket_name}/raw-data/surveys.csv")
    
    # Define the processing job
    script_processor = ScriptProcessor(
        command=['python3'],
        image_uri=f'737474898029.dkr.ecr.{region}.amazonaws.com/sagemaker-scikit-learn:0.23-1-cpu-py3',
        role=role,
        instance_count=1,
        instance_type='ml.m5.xlarge',
        sagemaker_session=sagemaker_session,
        base_job_name='survey-processing'
    )
    
    # Run the processing job
    script_processor.run(
        code='sagemaker_survey_processing.py',
        inputs=[
            ProcessingInput(
                source=f's3://{bucket_name}/raw-data/',
                destination='/opt/ml/processing/input'
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name='survey_output',
                source='/opt/ml/processing/output',
                destination=f's3://{bucket_name}/processed-data/surveys/'
            )
        ]
    )
    
    print("Survey processing job completed successfully")
    print(f"Results saved to: s3://{bucket_name}/processed-data/surveys/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run SageMaker survey processing job')
    parser.add_argument('--bucket', type=str, required=True, help='S3 bucket name')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    run_survey_processing_job(args.bucket, args.region)

