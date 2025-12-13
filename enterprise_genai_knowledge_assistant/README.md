# Enterprise GenAI Knowledge Assistant

A comprehensive AI-powered knowledge assistant built on AWS, leveraging Amazon Bedrock for generative AI capabilities, OpenSearch for vector search, and serverless architecture for scalability and cost-efficiency.

## Architecture Overview

This solution implements an enterprise-grade GenAI knowledge assistant with the following key components:

### Core Components

1. **Document Storage & Processing**
   - S3 bucket for document storage with versioning and encryption
   - Lambda function for document processing and embedding generation
   - Integration with Amazon Bedrock for text embeddings

2. **Vector Search Engine**
   - Amazon OpenSearch Service for vector similarity search
   - Secure configuration with encryption at rest and in transit
   - Fine-grained access control with IAM integration

3. **Conversational AI**
   - Query processing Lambda with Amazon Bedrock integration
   - DynamoDB for conversation history and context management
   - Support for multi-turn conversations with context retention

4. **API Layer**
   - API Gateway REST API with CORS support
   - Endpoints for document ingestion and query processing
   - CloudWatch logging and monitoring

5. **Monitoring & Observability**
   - CloudWatch Dashboard for system metrics
   - Custom alarms for error detection
   - Log aggregation and analysis

## Features

- **Document Ingestion**: Upload and process documents for knowledge base creation
- **Semantic Search**: Vector-based similarity search using OpenSearch
- **Conversational AI**: Multi-turn conversations with context awareness
- **Evaluation & Feedback**: Track and improve response quality
- **Security**: Encryption at rest and in transit, IAM-based access control
- **Scalability**: Serverless architecture that scales automatically
- **Cost Optimization**: Pay-per-use pricing with DynamoDB and Lambda

## Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0
- AWS CLI configured with credentials
- Access to Amazon Bedrock (ensure model access is enabled)
- Python 3.10 for Lambda functions

## Quick Start

### 1. Enable Amazon Bedrock Models

Before deploying, ensure you have enabled the required models in Amazon Bedrock:

1. Go to AWS Console → Amazon Bedrock → Model access
2. Request access to the following models:
   - `amazon.titan-embed-text-v1` (for embeddings)
   - `anthropic.claude-v2` or `anthropic.claude-3-sonnet` (for text generation)

### 2. Prepare Lambda Functions

Create the Lambda function directories with your application code:

```bash
# From the project root
mkdir -p lambda/document_processor
mkdir -p lambda/query_handler

# Add your Lambda function code
# See the Lambda Functions section below for implementation details
```

### 3. Configure Terraform

```bash
cd iac

# Copy the example tfvars file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your configuration
vim terraform.tfvars
```

### 4. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the planned changes
terraform plan

# Deploy the infrastructure
terraform apply
```

### 5. Retrieve Deployment Information

After successful deployment, get the API endpoints and other outputs:

```bash
terraform output
```

## Project Structure

```
enterprise_genai_knowledge_assistant/
├── iac/
│   ├── provider.tf           # AWS provider configuration
│   ├── variables.tf           # Input variables
│   ├── s3.tf                  # S3 bucket for documents
│   ├── opensearch.tf          # OpenSearch domain
│   ├── dynamodb.tf            # DynamoDB tables
│   ├── iam.tf                 # IAM roles and policies
│   ├── lambda.tf              # Lambda functions
│   ├── api_gateway.tf         # API Gateway configuration
│   ├── cloudwatch.tf          # Monitoring and alarms
│   ├── outputs.tf             # Output values
│   ├── state.tf               # State backend configuration
│   └── terraform.tfvars.example
├── lambda/
│   ├── document_processor/    # Document processing Lambda
│   │   ├── app.py
│   │   └── requirements.txt
│   └── query_handler/         # Query processing Lambda
│       ├── app.py
│       └── requirements.txt
└── README.md
```

## Lambda Functions

### Document Processor

The document processor Lambda function handles document ingestion and embedding generation.

**Key responsibilities:**
- Extract text from uploaded documents
- Generate embeddings using Amazon Bedrock
- Store embeddings in OpenSearch
- Update metadata in DynamoDB

**Environment variables:**
- `DOCUMENT_BUCKET`: S3 bucket for documents
- `METADATA_TABLE`: DynamoDB table for metadata
- `OPENSEARCH_DOMAIN`: OpenSearch endpoint
- `OPENSEARCH_SECRET`: Secret name for OpenSearch credentials
- `AWS_REGION`: AWS region

### Query Handler

The query handler Lambda function processes user queries and generates responses.

**Key responsibilities:**
- Generate query embeddings
- Search OpenSearch for relevant documents
- Generate contextual responses using Amazon Bedrock
- Maintain conversation history
- Store evaluation metrics

**Environment variables:**
- `METADATA_TABLE`: DynamoDB table for metadata
- `CONVERSATION_TABLE`: DynamoDB table for conversations
- `OPENSEARCH_DOMAIN`: OpenSearch endpoint
- `OPENSEARCH_SECRET`: Secret name for OpenSearch credentials
- `EVALUATION_TABLE`: DynamoDB table for evaluations
- `AWS_REGION`: AWS region

## API Endpoints

### POST /documents

Upload and process a document.

**Request:**
```json
{
  "document_id": "doc-123",
  "content": "Document content...",
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "category": "Category"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "document_id": "doc-123",
  "message": "Document processed successfully"
}
```

### POST /query

Submit a query to the knowledge assistant.

**Request:**
```json
{
  "query": "What is the return policy?",
  "conversation_id": "conv-456",
  "max_results": 5
}
```

**Response:**
```json
{
  "answer": "Based on our policy, returns are accepted within 30 days...",
  "sources": [
    {
      "document_id": "doc-123",
      "relevance_score": 0.95,
      "excerpt": "..."
    }
  ],
  "conversation_id": "conv-456"
}
```

## Configuration Options

### Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region to deploy | `us-east-1` |
| `environment` | Environment name | `dev` |
| `project_name` | Project name for resources | `genai-knowledge-assistant` |
| `opensearch_instance_type` | OpenSearch instance type | `r6g.large.search` |
| `opensearch_data_nodes` | Number of OpenSearch nodes | `2` |
| `opensearch_ebs_volume_size` | EBS volume size (GB) | `100` |
| `lambda_timeout` | Lambda timeout (seconds) | `60` |
| `lambda_memory_size` | Lambda memory (MB) | `1024` |
| `document_processor_timeout` | Document processor timeout | `300` |
| `conversation_ttl_days` | Conversation TTL (days) | `30` |

## Monitoring

### CloudWatch Dashboard

The deployment creates a comprehensive CloudWatch dashboard with:

- Lambda function metrics (invocations, errors, duration)
- API Gateway metrics (requests, errors, latency)
- DynamoDB capacity metrics
- OpenSearch cluster health
- Recent error logs

Access the dashboard: AWS Console → CloudWatch → Dashboards → `genai-knowledge-assistant-{environment}`

### Alarms

The following alarms are configured:

1. **Lambda Errors**: Triggers when Lambda errors exceed threshold
2. **API Gateway 5XX**: Alerts on server errors
3. **OpenSearch Cluster Red**: Monitors cluster health

## Security Considerations

1. **Encryption**
   - S3 buckets use server-side encryption (AES-256)
   - DynamoDB tables use AWS managed encryption
   - OpenSearch domain has encryption at rest enabled
   - All data in transit uses TLS 1.2+

2. **Access Control**
   - Lambda functions use least-privilege IAM roles
   - OpenSearch has fine-grained access control
   - API Gateway can be configured with API keys or Cognito

3. **Secrets Management**
   - OpenSearch credentials stored in AWS Secrets Manager
   - Automatic password rotation can be configured

4. **Network Security**
   - OpenSearch can be deployed in VPC (modify opensearch.tf)
   - Lambda functions can be configured with VPC access

## Cost Optimization

- DynamoDB uses on-demand billing (PAY_PER_REQUEST)
- Lambda functions scale to zero when not in use
- S3 lifecycle policies can be added for archival
- OpenSearch instance type can be adjusted based on workload
- Consider Reserved Capacity for production workloads

## Troubleshooting

### OpenSearch Connection Issues

If Lambda functions cannot connect to OpenSearch:

1. Check security groups and network configuration
2. Verify IAM permissions in `iam.tf`
3. Check OpenSearch access policies
4. Review Lambda function logs in CloudWatch

### Lambda Timeout Errors

If document processing times out:

1. Increase `document_processor_timeout` variable
2. Consider processing large documents asynchronously
3. Optimize embedding generation batch size

### Bedrock Access Denied

If you receive access denied errors:

1. Verify Bedrock model access is enabled in your account
2. Check IAM permissions for Bedrock API calls
3. Ensure you're using a supported region for Bedrock

## Clean Up

To destroy all resources:

```bash
cd iac
terraform destroy
```

**Note**: This will permanently delete all data including:
- S3 bucket contents
- DynamoDB tables
- OpenSearch domain
- CloudWatch logs

## Next Steps

1. **Implement Lambda Functions**: Add your business logic to the Lambda functions
2. **Add Authentication**: Configure API Gateway with Cognito or API keys
3. **Enable X-Ray**: Add distributed tracing for debugging
4. **Set Up CI/CD**: Automate deployments with AWS CodePipeline
5. **Configure Backups**: Set up automated backups for DynamoDB and OpenSearch
6. **Add Rate Limiting**: Implement throttling for API Gateway
7. **Enable Caching**: Configure API Gateway caching for improved performance

## Support

For issues or questions:
- Check CloudWatch logs for detailed error messages
- Review AWS service quotas if you encounter limits
- Consult AWS documentation for service-specific issues

## License

This project is provided as-is for educational and development purposes.

