import boto3
import json

# Initialize clients
s3 = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime')


def process_document(bucket, key, model_id='amazon.nova-micro-v1:0'):
    # Get document from S3
    response = s3.get_object(Bucket=bucket, Key=key)
    document_text = response['Body'].read().decode('utf-8')
    
    # Create prompt for information extraction
    prompt = f"""
    Extract the following information from this insurance claim document:
    - Claimant Name
    - Policy Number
    - Incident Date
    - Claim Amount
    - Incident Description
    
    Document:
    {document_text}
    
    Return the information in JSON format.
    """
    
    # Invoke Bedrock model (using Messages API for Nova)
    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "temperature": 0.0,
                "maxTokens": 1000
            }
        })
    )
    
    # Parse response
    print(response)
    response_body = json.loads(response['body'].read())
    # Handle Messages API response structure
    extracted_info = response_body['output']['message']['content'][0]['text']
    
    # Generate summary
    summary_prompt = f"""
    Based on this extracted information:
    {extracted_info}
    
    Generate a concise summary of the claim.
    """
    
    summary_response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": summary_prompt}]
                }
            ],
            "inferenceConfig": {
                "temperature": 0.7,
                "maxTokens": 500
            }
        })
    )
    
    summary_body = json.loads(summary_response['body'].read())
    summary = summary_body['output']['message']['content'][0]['text']
    
    return {
        "extracted_info": extracted_info,
        "summary": summary
    }

# Example usage
if __name__ == "__main__":
    result = process_document('claim-documents-poc-ars', 'claims/claim1.txt')
    print(json.dumps(result, indent=2))


