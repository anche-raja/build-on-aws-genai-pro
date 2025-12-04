# Build on AWS GenAI Pro

A comprehensive collection of Proof of Concepts (PoCs) and hands-on labs designed to help you master the domains of the **AWS Certified Generative AI Developer - Professional** exam.

## Repository Structure

### Domain 1: Fundamentals of Generative AI

#### **[01_1.1_claim_processing_poc](./01_1.1_claim_processing_poc/README.md)** - Insurance Claim Processing
*   **Scenario**: Automated insurance claim processing with document analysis and policy validation
*   **Skills**: Designing GenAI architectures, implementing PoCs, and creating reusable components (Skills 1.1.1 - 1.1.3)
*   **Tech Stack**: Amazon Bedrock, Python (Boto3), Prompt Engineering, RAG (Retrieval Augmented Generation)
*   **Key Concepts**: Prompt templates, document processing, policy validation, structured outputs

#### **[01_1.2_resilient_dynamic_routing_system](./01_1.2_resilient_dynamic_routing_system/README.md)** - Model Selection & Routing
*   **Scenario**: Intelligent model selection with fallback mechanisms and continuous evaluation
*   **Skills**: Model selection strategies, resilient architecture patterns, and continuous evaluation (Skills 1.2.1 - 1.2.3)
*   **Tech Stack**: Amazon Bedrock, AWS Step Functions, AWS AppConfig, AWS Lambda, Terraform
*   **Key Concepts**: Dynamic routing, fallback patterns, model evaluation, cost optimization

#### **[01_1.3_data_validate_processing](./01_1.3_data_validate_processing/README.md)** - Multimodal Data Processing Pipeline ⭐ NEW
*   **Scenario**: Production-grade data validation and multimodal processing for GenAI applications
*   **Skills**: Data quality gates, event-driven architecture, multimodal data processing, infrastructure automation
*   **Tech Stack**: 
    - **Validation**: AWS Glue Data Quality, Lambda, S3 Events
    - **AI Services**: Amazon Comprehend, Textract, Rekognition, Transcribe
    - **Processing**: Lambda Functions (5), SageMaker Processing, EventBridge
    - **Infrastructure**: Terraform, CloudWatch Dashboard
*   **Key Concepts**: 
    - Dual-layer validation (real-time + batch)
    - Event-driven serverless architecture
    - Multi-modal processing (text, images, audio, surveys)
    - Data quality assurance for ML/AI pipelines
    - NLP entity extraction, sentiment analysis
    - OCR and image analysis
    - Speech-to-text with speaker diarization
*   **Data Types Supported**:
    - 📝 Text reviews → Comprehend NLP (entities, sentiment, key phrases)
    - 🖼️ Product images → Textract OCR + Rekognition labels
    - 🎵 Audio calls → Transcribe + Comprehend analysis
    - 📊 Survey data → SageMaker batch processing

## Reference Materials

The `pdfs/` directory contains essential AWS documentation:

- **AWS WA Tool Generative AI Lens** - Well-Architected Framework for GenAI
- **AWS Certified Generative AI Developer Pro Exam Guide** - Official exam preparation
- **Bedrock User Guide** - Comprehensive Bedrock documentation

## Troubleshooting

### Common Issues

**AWS Credentials Not Configured**
```bash
aws configure
# Enter your AWS Access Key ID, Secret Key, Region
```

**Bedrock Model Access Denied**
- Go to AWS Bedrock Console → Model access
- Request access to Claude, Nova, and other models
- Wait for approval (usually instant for Nova models)

**Terraform State Issues**
```bash
cd iac/
terraform init -reconfigure
```

**Lambda Timeout Errors**
- Check CloudWatch Logs: `/aws/lambda/<FunctionName>`
- Increase timeout in Terraform configuration
- Verify IAM permissions

**S3 Bucket Already Exists**
- Change `project_bucket_name` in `terraform.tfvars`
- Use unique bucket name with your initials

### Getting Help

1. **Check CloudWatch Logs** for detailed error messages
2. **Review project README** for specific troubleshooting sections
3. **Verify AWS service limits** in your account
4. **Check IAM permissions** for all required services

## Best Practices

### Security
- ✅ Use IAM roles with least-privilege permissions
- ✅ Enable S3 bucket encryption
- ✅ Use Secrets Manager for API keys (not in code)
- ✅ Enable CloudTrail for audit logging
- ✅ Review security groups and network ACLs

### Cost Optimization
- ✅ Use serverless services (pay-per-use)
- ✅ Set up billing alarms
- ✅ Delete resources after testing (`terraform destroy`)
- ✅ Use appropriate Lambda memory configurations
- ✅ Implement quality gates to avoid wasted processing

### Monitoring
- ✅ Use CloudWatch Dashboards for visualization
- ✅ Set up alarms for critical metrics
- ✅ Enable detailed logging
- ✅ Track costs with AWS Cost Explorer
- ✅ Monitor API throttling and limits

### Development
- ✅ Test locally before deploying
- ✅ Use version control (Git)
- ✅ Document changes and configurations
- ✅ Use Infrastructure as Code (Terraform)
- ✅ Implement proper error handling

## Contributing

This is a learning repository. Feel free to:
- Fork and experiment
- Add your own improvements
- Create additional use cases
- Share feedback and suggestions

## Additional Resources

### AWS Documentation
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [Amazon Comprehend Documentation](https://docs.aws.amazon.com/comprehend/)
- [AWS Glue Data Quality](https://docs.aws.amazon.com/glue/latest/dg/glue-data-quality.html)

### Certification Prep
- [AWS Certified GenAI Developer - Professional](https://aws.amazon.com/certification/certified-generative-ai-developer-professional/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Architecture Center](https://aws.amazon.com/architecture/)

### Community
- [AWS re:Post](https://repost.aws/)
- [AWS Blog - AI/ML](https://aws.amazon.com/blogs/machine-learning/)
- [AWS Samples GitHub](https://github.com/aws-samples)

## Cleanup

To avoid ongoing costs, clean up resources after testing:

```bash
# For each project with Terraform
cd 01_1.3_data_validate_processing/iac
terraform destroy -auto-approve

cd ../../01_1.2_resilient_dynamic_routing_system/iac
terraform destroy -auto-approve

# Verify no resources remain
aws lambda list-functions --query 'Functions[].FunctionName'
aws s3 ls | grep customer-feedback
```

**Important**: S3 buckets with data cannot be deleted until emptied.

## License

This project is for educational purposes as part of AWS GenAI certification preparation.

## Acknowledgments

Built for the AWS Certified Generative AI Developer - Professional certification preparation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GENAI APPLICATION STACK                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  01_1.1         │  │  01_1.2         │  │  01_1.3         │    │
│  │  Claim          │  │  Model          │  │  Data           │    │
│  │  Processing     │  │  Routing        │  │  Processing     │    │
│  │                 │  │                 │  │                 │    │
│  │  • RAG          │  │  • Dynamic      │  │  • Validation   │    │
│  │  • Prompts      │  │  • Fallback     │  │  • Multimodal   │    │
│  │  • Validation   │  │  • Evaluation   │  │  • NLP/OCR/STT  │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│           │                     │                      │            │
│           └─────────────────────┴──────────────────────┘            │
│                                 │                                   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │   Foundation Models       │
                    │   (Amazon Bedrock)        │
                    └──────────────────────────┘
```

## Project Progression

Each project builds upon the previous, teaching progressively more advanced concepts:

1. **Start Here** → `01_1.1_claim_processing_poc`
   - Learn: Basic GenAI integration, prompts, RAG
   - Time: 1-2 hours
   - Complexity: ⭐⭐☆☆☆

2. **Then** → `01_1.2_resilient_dynamic_routing_system`
   - Learn: Model selection, resilience patterns, orchestration
   - Time: 2-3 hours
   - Complexity: ⭐⭐⭐☆☆

3. **Finally** → `01_1.3_data_validate_processing`
   - Learn: Production data pipelines, multimodal processing, quality gates
   - Time: 2-3 hours
   - Complexity: ⭐⭐⭐⭐☆

## Getting Started

### Prerequisites

**AWS Account Setup**:
- AWS Account with appropriate permissions
- Amazon Bedrock access (ensure Nova Micro/Lite models are enabled)
- IAM permissions for Lambda, S3, Glue, Comprehend, Textract, Rekognition, Transcribe

**Local Development**:
- Python 3.11+ installed
- AWS CLI configured with credentials
- Terraform ≥ 1.6 (for infrastructure projects)
- boto3, pandas (install via `pip install -r requirements.txt`)

### Quick Start Options

**Option 1: Follow the Learning Path** (Recommended for beginners)
```bash
# Start with claim processing
cd 01_1.1_claim_processing_poc
# Follow README.md

# Move to model routing
cd ../01_1.2_resilient_dynamic_routing_system
# Follow README.md

# Finally, data processing
cd ../01_1.3_data_validate_processing
# See QUICK_START.md for 5-minute deployment
```

**Option 2: Jump to Specific Topic**
```bash
# For data processing and validation
cd 01_1.3_data_validate_processing
terraform -chdir=iac init
terraform -chdir=iac apply
```

**Option 3: Just Browse**
- Each project has comprehensive documentation
- Sample data included for testing
- Architecture diagrams and flow charts provided

## Repository Features

✅ **Production-Ready Code**: All Lambda functions, scripts, and IaC tested and linted  
✅ **Complete Documentation**: READMEs, deployment guides, troubleshooting  
✅ **Sample Data**: Ready-to-use test files for all projects  
✅ **Infrastructure as Code**: Terraform for reproducible deployments  
✅ **Cost-Optimized**: Serverless architectures with pay-per-use pricing  
✅ **Best Practices**: Error handling, logging, monitoring, security  

## Key Technologies

| Category | Technologies |
|----------|-------------|
| **Foundation Models** | Amazon Bedrock (Claude, Nova, Llama) |
| **AI/ML Services** | Comprehend, Textract, Rekognition, Transcribe |
| **Compute** | Lambda Functions, SageMaker Processing |
| **Storage** | S3, DynamoDB |
| **Data Quality** | AWS Glue Data Quality, Data Catalog |
| **Orchestration** | Step Functions, EventBridge |
| **Monitoring** | CloudWatch Logs, Metrics, Dashboards |
| **IaC** | Terraform |
| **Languages** | Python 3.11+ |

## Learning Outcomes

By completing these projects, you will:

### GenAI Fundamentals
✅ Design and implement GenAI architectures  
✅ Create effective prompts and prompt templates  
✅ Implement RAG (Retrieval Augmented Generation)  
✅ Build validation and quality checks  

### Production Patterns
✅ Event-driven serverless architectures  
✅ Model selection and routing strategies  
✅ Fallback and resilience patterns  
✅ Multi-layer data validation  

### AWS Services Mastery
✅ Amazon Bedrock model invocation and configuration  
✅ AWS Lambda function development and deployment  
✅ S3 event notifications and triggers  
✅ Step Functions state machine orchestration  
✅ Glue Data Quality and Data Catalog  
✅ Comprehend NLP APIs  
✅ Textract OCR processing  
✅ Rekognition image analysis  
✅ Transcribe speech-to-text  
✅ SageMaker Processing jobs  
✅ EventBridge rules and targets  
✅ CloudWatch monitoring and dashboards  

### Infrastructure & DevOps
✅ Infrastructure as Code with Terraform  
✅ IAM roles and least-privilege policies  
✅ CloudWatch monitoring and alerting  
✅ Cost optimization strategies  
✅ Troubleshooting and debugging  

## Project Highlights

### 01_1.1 - Claim Processing
- **What**: Automated insurance claim processing
- **Highlight**: RAG implementation with policy validation
- **Output**: Structured claim decisions with explanations

### 01_1.2 - Model Routing
- **What**: Intelligent model selection with fallbacks
- **Highlight**: Step Functions orchestration with AppConfig
- **Output**: Optimized model routing based on task complexity

### 01_1.3 - Data Processing ⭐
- **What**: Multimodal data validation and processing pipeline
- **Highlight**: 4 data types processed with 5 Lambda functions
- **Output**: Enriched, structured data ready for Foundation Models

**Unique Features**:
- Processes text, images, audio, and surveys
- Dual-layer quality validation (real-time + batch)
- Event-driven with automatic scaling
- Complete sample data and testing guides
- Production-ready with monitoring

## Cost Estimates

Estimated costs for testing all projects (running ~100 operations each):

| Project | Testing Cost | Production Cost/Day |
|---------|-------------|-------------------|
| 01_1.1 Claim Processing | $0.10 | $5-10 |
| 01_1.2 Model Routing | $0.20 | $10-20 |
| 01_1.3 Data Processing | $0.50 | $8-15 |
| **Total** | **~$0.80** | **$25-45** |

*Costs assume moderate usage. Actual costs vary based on data volume and model usage.*

## Certification Alignment

This repository is structured to cover key domains of the **AWS Certified Generative AI Developer - Professional** exam:

- ✅ Domain 1.1: Design and architect GenAI solutions
- ✅ Domain 1.2: Select and manage foundation models
- ✅ Domain 1.3: Data preparation and quality assurance
- ✅ Hands-on implementation experience
- ✅ Production-ready patterns and best practices

## Navigation

### For Each Project

1. **Navigate to project directory**
   ```bash
   cd 01_1.3_data_validate_processing
   ```

2. **Read the documentation**
   - `README.md` - Main project documentation
   - `QUICK_START.md` - Fast deployment (01_1.3 only)
   - `DEPLOYMENT_GUIDE.md` - Detailed setup (01_1.3 only)

3. **Deploy and test**
   - Follow step-by-step instructions
   - Use provided sample data
   - Monitor via CloudWatch

4. **Clean up**
   ```bash
   terraform destroy  # For infrastructure projects
   ```
