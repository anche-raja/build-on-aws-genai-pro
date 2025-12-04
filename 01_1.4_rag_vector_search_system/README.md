# RAG Vector Search System with Amazon Bedrock

A production-grade Retrieval-Augmented Generation (RAG) system built on AWS, leveraging Amazon Bedrock for foundation models and embeddings, Amazon OpenSearch for vector search, and comprehensive infrastructure automation.

## 🎯 Project Overview

This project implements a complete end-to-end RAG system following AWS best practices. It demonstrates how to build scalable, secure, and maintainable AI applications using AWS managed services.

### Key Features

- ✅ **Multiple Vector Database Options**: Amazon Bedrock Knowledge Bases or Amazon OpenSearch Service
- ✅ **Advanced Document Processing**: Support for PDF, DOCX, TXT, and HTML with multiple chunking strategies
- ✅ **Automated Sync Pipeline**: EventBridge + Step Functions for scheduled updates and change detection
- ✅ **Production-Ready Infrastructure**: Complete Terraform IaC with security best practices
- ✅ **Flexible Retrieval Strategies**: Semantic search, hybrid search, and metadata filtering
- ✅ **REST API**: API Gateway + Lambda for easy integration
- ✅ **Data Source Connectors**: Web crawler, Confluence, and MediaWiki integrations
- ✅ **Monitoring & Analytics**: CloudWatch dashboards and logs

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Phases Overview](#phases-overview)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Usage Examples](#usage-examples)
- [Cost Estimation](#cost-estimation)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User/Application                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │   API Gateway        │
                    │   REST API           │
                    └───────────┬──────────┘
                                │
                    ┌───────────▼──────────┐
                    │   Lambda (RAG API)   │
                    │   Query Processing   │
                    └───────────┬──────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│  Amazon        │    │  Amazon         │    │  DynamoDB       │
│  Bedrock       │    │  OpenSearch     │    │  Metadata       │
│  - Claude 3    │    │  - Vector Search│    │  - Doc Info     │
│  - Titan Embed │    │  - Neural Search│    │  - Tracking     │
└────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │   S3 Document Store  │
                    │   - Raw Documents    │
                    │   - Versioning       │
                    └───────────┬──────────┘
                                │
                    ┌───────────▼──────────┐
                    │   Lambda Processor   │
                    │   - Extract Text     │
                    │   - Chunking         │
                    │   - Embeddings       │
                    └──────────────────────┘
```

### Data Flow

1. **Document Ingestion**: Documents uploaded to S3 trigger Lambda processor
2. **Processing**: Extract text, chunk, generate embeddings
3. **Storage**: Store embeddings in OpenSearch/Bedrock KB, metadata in DynamoDB
4. **Query**: User sends query via API Gateway
5. **Retrieval**: Generate query embedding, search vector database
6. **Generation**: Augment context, invoke foundation model
7. **Response**: Return answer with sources

## 📦 Prerequisites

### AWS Account Requirements

- AWS Account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Amazon Bedrock model access enabled (see [Enable Model Access](#enable-bedrock-model-access))

### Software Requirements

- **Terraform** >= 1.0 ([Install](https://www.terraform.io/downloads))
- **Python** >= 3.11 ([Install](https://www.python.org/downloads/))
- **AWS CLI** >= 2.0 ([Install](https://aws.amazon.com/cli/))
- **Git** (for cloning the repository)

### Python Dependencies

```bash
pip install -r requirements.txt
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Navigate to project directory
cd 01_1.4_rag_vector_search_system

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Enable Bedrock Model Access

1. Navigate to **Amazon Bedrock Console** → **Model access**
2. Request access to:
   - Amazon Titan Embeddings G1 - Text
   - Anthropic Claude 3 Sonnet
   - (Optional) Other models you want to use

### 3. Configure Infrastructure

```bash
# Copy example config
cp iac/terraform.tfvars.example iac/terraform.tfvars

# Edit terraform.tfvars with your settings
nano iac/terraform.tfvars
```

Required configuration:
```hcl
aws_region           = "us-east-1"
document_bucket_name = "your-unique-bucket-name"  # Must be globally unique
```

### 4. Deploy Infrastructure

#### Option A: Automated Setup (Recommended)

```bash
# Run the setup script
./setup_infrastructure.sh
```

#### Option B: Manual Deployment

```bash
# Package Lambda functions
cd app && zip -r ../lambda_document_processor.zip . && cd ..
zip -g lambda_document_processor.zip lambda_document_processor.py

cd app && zip -r ../lambda_sync_scheduler.zip . && cd ..
zip -g lambda_sync_scheduler.zip lambda_sync_scheduler.py

cd app && zip -r ../lambda_rag_api.zip . && cd ..
zip -g lambda_rag_api.zip lambda_rag_api.py

# Deploy with Terraform
cd iac
terraform init
terraform plan
terraform apply
```

### 5. Upload Sample Documents

```bash
# Get bucket name from Terraform output
BUCKET_NAME=$(cd iac && terraform output -raw s3_bucket_name)

# Upload sample documents
aws s3 cp sample-data/sample_doc1.txt s3://$BUCKET_NAME/documents/
aws s3 cp sample-data/sample_doc2.txt s3://$BUCKET_NAME/documents/
```

### 6. Test the API

```bash
# Get API endpoint
API_URL=$(cd iac && terraform output -raw api_gateway_url)

# Test query
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Amazon Bedrock?",
    "num_results": 3
  }'
```

## 📁 Project Structure

```
01_1.4_rag_vector_search_system/
├── app/                           # Application modules
│   ├── __init__.py
│   ├── bedrock_manager.py         # Bedrock API wrapper
│   ├── opensearch_manager.py      # OpenSearch operations
│   ├── metadata_manager.py        # DynamoDB metadata operations
│   ├── document_processor.py      # Document processing & chunking
│   ├── web_crawler.py             # Web scraping connector
│   ├── wiki_connector.py          # Wiki system integrations
│   ├── sync_manager.py            # Data synchronization
│   └── rag_application.py         # Complete RAG orchestration
│
├── iac/                           # Infrastructure as Code (Terraform)
│   ├── provider.tf                # Terraform & AWS provider config
│   ├── variables.tf               # Input variables
│   ├── terraform.tfvars.example   # Example configuration
│   ├── s3.tf                      # S3 bucket for documents
│   ├── dynamodb.tf                # DynamoDB tables
│   ├── opensearch.tf              # OpenSearch domain
│   ├── iam.tf                     # IAM roles and policies
│   ├── lambda.tf                  # Lambda functions
│   ├── api_gateway.tf             # API Gateway configuration
│   ├── step_functions.tf          # Step Functions workflows
│   ├── eventbridge.tf             # EventBridge rules
│   └── outputs.tf                 # Output values
│
├── lambda_document_processor.py   # Lambda: Process uploaded documents
├── lambda_sync_scheduler.py       # Lambda: Scheduled sync checks
├── lambda_rag_api.py              # Lambda: RAG query API
│
├── config/                        # Configuration files
│   ├── chunking_strategies.json   # Chunking configurations
│   └── model_config.json          # Model selections & settings
│
├── sample-data/                   # Sample documents and tests
│   ├── sample_doc1.txt            # Sample document 1
│   ├── sample_doc2.txt            # Sample document 2
│   └── test_query.json            # Test queries
│
├── requirements.txt               # Python dependencies
├── setup_infrastructure.sh        # Automated setup script
└── README.md                      # This file
```

## 📖 Phases Overview

This project implements a complete RAG system across 6 phases:

### Phase 1: Foundation Infrastructure
- Amazon Bedrock setup and configuration
- OpenSearch Service domain with vector search
- DynamoDB metadata tables
- S3 bucket for document storage

**Key Components**: `bedrock_manager.py`, `opensearch_manager.py`, `metadata_manager.py`

### Phase 2: Document Processing Pipeline
- Multi-format document extraction (PDF, DOCX, HTML, TXT)
- Advanced chunking strategies (semantic, fixed, paragraph, sliding window)
- Embedding generation and storage
- Metadata extraction and enrichment

**Key Components**: `document_processor.py`, `lambda_document_processor.py`

### Phase 3: Advanced Vector Search
- Hierarchical document indexing
- Multi-index search strategies
- Hybrid search (keyword + semantic)
- Query optimization and caching

**Key Components**: `opensearch_manager.py` (vector_search, hybrid_search methods)

### Phase 4: Data Source Integration
- Web crawler for public documentation
- Confluence connector
- MediaWiki connector
- Unified data catalog

**Key Components**: `web_crawler.py`, `wiki_connector.py`

### Phase 5: Data Maintenance
- Change detection (checksums, version tracking)
- Incremental update pipeline
- Scheduled refresh workflows (EventBridge + Step Functions)
- Stale document detection and cleanup

**Key Components**: `sync_manager.py`, `lambda_sync_scheduler.py`, Step Functions

### Phase 6: RAG Application
- Context retrieval and optimization
- Prompt engineering
- Foundation model integration
- REST API with API Gateway
- Conversation history support
- Feedback collection

**Key Components**: `rag_application.py`, `lambda_rag_api.py`, API Gateway

## ⚙️ Configuration

### Chunking Strategies

Configure in `config/chunking_strategies.json`:

- **Semantic** (Recommended): Preserves sentence boundaries
- **Fixed Size**: Simple character-based chunking
- **Paragraph**: Natural paragraph boundaries
- **Sliding Window**: Overlapping windows for dense content

### Model Selection

Configure in `config/model_config.json`:

**Embedding Models**:
- `amazon.titan-embed-text-v1` (Recommended): 1536 dimensions, 8K tokens
- `cohere.embed-english-v3`: 1024 dimensions, English-optimized
- `cohere.embed-multilingual-v3`: Multilingual support

**Foundation Models**:
- `anthropic.claude-3-sonnet` (Recommended): Balanced performance/cost
- `anthropic.claude-3-haiku`: Fast, cost-effective
- `anthropic.claude-3-opus`: Highest accuracy
- `amazon.titan-text-express`: AWS-native option

### RAG Configurations

Pre-configured profiles:
- **Balanced**: Best for most use cases
- **Cost Optimized**: Minimize costs
- **High Accuracy**: Maximum quality
- **Fast Response**: Prioritize speed

## 🚢 Deployment

### Development Environment

```bash
terraform apply -var="environment=dev"
```

### Production Environment

```bash
# Use production-grade settings
terraform apply -var="environment=prod" \
  -var="opensearch_instance_count=3" \
  -var="opensearch_instance_type=r6g.xlarge.search"
```

### Multi-Region Deployment

Deploy to multiple regions for disaster recovery:

```bash
# Primary region
cd iac
terraform workspace new us-east-1
terraform apply -var="aws_region=us-east-1"

# Secondary region
terraform workspace new us-west-2
terraform apply -var="aws_region=us-west-2"
```

## 💡 Usage Examples

### 1. Python SDK

```python
from app.rag_application import RAGApplication
from app.bedrock_manager import BedrockManager
from app.opensearch_manager import OpenSearchManager

# Initialize
bedrock = BedrockManager(region_name='us-east-1')
opensearch = OpenSearchManager(domain_endpoint='your-endpoint')
rag_app = RAGApplication(bedrock, opensearch)

# Query
response = rag_app.generate_response(
    query="What is Amazon Bedrock?",
    index_name="documents",
    num_context_chunks=5
)

print(f"Answer: {response['answer']}")
print(f"Sources: {len(response['sources'])}")
```

### 2. REST API

```bash
# Simple query
curl -X POST https://your-api-endpoint/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do vector embeddings work?",
    "num_results": 5
  }'

# With metadata filters
curl -X POST https://your-api-endpoint/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Amazon Bedrock pricing",
    "num_results": 3,
    "filters": {
      "metadata.document_type": "documentation"
    }
  }'

# Conversation mode
curl -X POST https://your-api-endpoint/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Can I customize the models?",
    "conversation_history": [
      {
        "role": "user",
        "content": "What is Amazon Bedrock?"
      },
      {
        "role": "assistant",
        "content": "Amazon Bedrock is a fully managed service..."
      }
    ]
  }'
```

### 3. Web Crawler Integration

```python
from app.web_crawler import WebCrawler

# Initialize crawler
crawler = WebCrawler(delay=2.0, max_depth=3)

# Crawl website
pages = crawler.crawl_website(
    start_url="https://docs.aws.amazon.com/bedrock/",
    max_pages=50,
    url_patterns=["/latest/userguide/"]
)

# Process and index
for page in pages:
    # Process with document_processor
    # Index to vector database
    pass
```

### 4. Confluence Integration

```python
from app.wiki_connector import ConfluenceConnector

# Initialize connector
confluence = ConfluenceConnector(
    base_url="https://your-domain.atlassian.net/wiki",
    username="your-email@example.com",
    api_token="your-api-token"
)

# Get pages from space
pages = confluence.list_pages(space_key="DOCS")

# Retrieve and index content
for page in pages:
    full_page = confluence.get_page(page['id'])
    # Process and index
```

## 💰 Cost Estimation

### Monthly Cost Breakdown (Approximate)

**Compute & Storage**:
- OpenSearch (3x r6g.large, 300GB): ~$600/month
- Lambda (10K requests/day): ~$5/month
- DynamoDB (On-demand, 100K reads/writes): ~$25/month
- S3 (100GB storage, 1K requests): ~$3/month

**AI Services** (usage-based):
- Bedrock Embeddings (1M tokens): ~$0.10
- Claude 3 Sonnet (1M input + 200K output tokens): ~$6
- Knowledge Base (if used): Variable

**Networking & Other**:
- API Gateway (1M requests): ~$3.50/month
- CloudWatch Logs (5GB): ~$2.50/month
- Data Transfer: ~$10-50/month

**Estimated Total**: ~$650-700/month for moderate usage

### Cost Optimization Tips

1. **Use Bedrock Knowledge Base instead of OpenSearch** for smaller workloads
2. **Enable S3 Intelligent-Tiering** for document storage
3. **Use Claude 3 Haiku** for cost-sensitive applications
4. **Implement caching** for frequent queries
5. **Use provisioned throughput** for predictable workloads

## 🔧 Troubleshooting

### Common Issues

#### 1. "Model access denied" error

**Solution**: Enable model access in Amazon Bedrock console
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1
```

#### 2. OpenSearch cluster yellow/red status

**Solution**: Check instance health and shard allocation
```bash
# Get cluster health
aws opensearch describe-domain --domain-name rag-vector-search-domain
```

#### 3. Lambda timeout errors

**Solution**: Increase timeout or optimize chunk size
```hcl
# In terraform.tfvars
lambda_timeout = 300  # Increase to 5 minutes
```

#### 4. S3 trigger not working

**Solution**: Verify Lambda permissions
```bash
aws lambda get-policy --function-name rag-vector-search-document-processor
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Viewing Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/rag-vector-search-document-processor --follow

# API Gateway logs
aws logs tail /aws/api-gateway/rag-vector-search --follow

# Step Functions executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:rag-vector-search-sync-workflow
```

## ✅ Best Practices

### Security

1. **Enable encryption**: All resources use encryption at rest and in transit
2. **Least privilege IAM**: IAM roles follow principle of least privilege
3. **VPC deployment**: For production, deploy OpenSearch in VPC
4. **API authentication**: Add API Gateway authorizer for production
5. **Secrets management**: Use Secrets Manager for credentials

### Performance

1. **Chunk size**: Keep chunks between 500-1000 characters
2. **Overlap**: Use 10-20% overlap for better context preservation
3. **Caching**: Implement caching for frequent queries
4. **Batch processing**: Use batch APIs for bulk operations
5. **Index optimization**: Regularly optimize OpenSearch indices

### Operational

1. **Monitoring**: Set up CloudWatch alarms for key metrics
2. **Backups**: Enable automated backups for DynamoDB and OpenSearch
3. **Versioning**: Keep S3 versioning enabled
4. **Documentation**: Maintain documentation for custom configurations
5. **Testing**: Regularly test with sample queries

### Cost Optimization

1. **Right-sizing**: Monitor and adjust resource sizes
2. **Cleanup**: Remove unused documents and indices
3. **Caching**: Reduce redundant API calls
4. **Compression**: Enable compression for S3 objects
5. **Reserved capacity**: Use reserved instances for predictable workloads

## 📚 Additional Resources

### AWS Documentation
- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/)
- [Amazon OpenSearch Service Guide](https://docs.aws.amazon.com/opensearch-service/)
- [RAG with Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)

### Related Projects
- [LangChain](https://github.com/langchain-ai/langchain)
- [LlamaIndex](https://github.com/run-llama/llama_index)
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel)

### Learning Resources
- [AWS Generative AI Learning Plan](https://aws.amazon.com/training/learn-about/generative-ai/)
- [Vector Database Fundamentals](https://www.pinecone.io/learn/vector-database/)
- [RAG Best Practices](https://www.anthropic.com/index/retrieval-augmented-generation)

## 🤝 Contributing

This project is part of the AWS GenAI Professional training program. Contributions and improvements are welcome!

## 📄 License

This project is provided as-is for educational purposes.

## 📧 Support

For issues and questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review AWS service documentation
3. Check CloudWatch logs for detailed error messages

---

**Built with ❤️ using AWS Managed Services**

