# AWS Customer Support AI Assistant

A production-ready customer support AI assistant built with Amazon Bedrock, implementing advanced prompt engineering strategies and comprehensive governance controls.

## 🎯 Project Overview

This project implements a sophisticated AI-powered customer support system that helps users troubleshoot AWS service issues while maintaining responsible AI practices through guardrails, quality validation, and iterative improvement mechanisms.

### Key Features

- **🤖 Intelligent Intent Detection**: Automatically identifies user needs using Amazon Comprehend and custom classification
- **🛡️ Comprehensive Guardrails**: Prevents security credential sharing, future feature commitments, and inappropriate competitor discussions
- **📊 Quality Assurance**: Automated validation of responses against predefined quality criteria
- **🔄 Iterative Improvement**: Feedback collection and analysis system for continuous prompt optimization
- **📝 Prompt Management**: Version-controlled prompt templates with approval workflows
- **🔍 Observability**: Full monitoring with CloudWatch, CloudTrail, and X-Ray
- **⚡ Serverless Architecture**: Scalable, cost-effective deployment using AWS serverless services

## 🏗️ Architecture

The system uses a Step Functions-orchestrated workflow with the following components:

```
User Query → API Gateway → Step Functions Workflow
                              ├─ Capture Query (Lambda)
                              ├─ Detect Intent (Lambda + Comprehend)
                              ├─ Generate Response (Lambda + Bedrock)
                              ├─ Validate Quality (Lambda)
                              └─ Collect Feedback (Lambda)
                              
Supporting Services:
- DynamoDB: Conversation history, prompt metadata, feedback storage
- S3: Prompt template storage with versioning
- CloudWatch: Monitoring and logging
- EventBridge: Scheduled feedback analysis
- CloudTrail: Audit logging
```

## 📋 Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0
- Python 3.11+
- AWS CLI configured
- Access to Amazon Bedrock (Claude 3 Sonnet recommended)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd 01_1.5_customer_support_ai_assistant
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Terraform Variables

```bash
cd iac
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings
```

### 4. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 5. Test the API

After deployment, use the test command from Terraform output:

```bash
# Get the API endpoint
terraform output api_gateway_url

# Test the assistant
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My EC2 instance is not responding to SSH connections",
    "user_id": "test-user-123"
  }'
```

## 📚 Documentation

- [**ARCHITECTURE.md**](ARCHITECTURE.md) - Detailed architecture and design decisions
- [**DEPLOYMENT_GUIDE.md**](DEPLOYMENT_GUIDE.md) - Step-by-step deployment instructions
- [**PROMPT_MANAGEMENT.md**](PROMPT_MANAGEMENT.md) - Guide to managing and optimizing prompts
- [**TESTING_GUIDE.md**](TESTING_GUIDE.md) - Testing strategies and test cases

## 🧪 Running Tests

```bash
# Run all tests
./tests/run_tests.sh

# Run specific test file
python -m pytest tests/test_intent_detector.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

## 📊 Monitoring and Observability

### CloudWatch Dashboard

Access the pre-configured dashboard:
```bash
terraform output dashboard_url
```

### Key Metrics

- **Execution Success Rate**: Percentage of successful workflow executions
- **Average Response Time**: End-to-end latency
- **Intent Confidence**: Average confidence scores for intent detection
- **Quality Scores**: Average quality validation scores
- **User Satisfaction**: Feedback ratings and sentiment

### Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/customer-support-ai-capture-query-dev --follow

# View Step Functions logs
aws logs tail /aws/stepfunctions/customer-support-ai-workflow-dev --follow
```

## 🛡️ Guardrails Implementation

The system implements three types of guardrails:

### 1. Content Filtering
- Detects and blocks security credentials (access keys, passwords, private keys)
- Prevents sharing of sensitive information

### 2. Topic Detection
- Blocks discussions about future AWS features
- Prevents commitments about roadmap items
- Restricts direct account modifications

### 3. Semantic Boundaries
- Ensures professional, factual competitor discussions
- Maintains appropriate tone and boundaries

## 🔄 Prompt Management

### Creating New Prompts

```python
from app.bedrock_prompt_manager import BedrockPromptManager

manager = BedrockPromptManager(
    region='us-east-1',
    s3_bucket='your-prompt-bucket',
    dynamodb_table='your-prompt-table'
)

# Create new template
template = {
    'name': 'VPC Troubleshooting',
    'template': '...',
    'parameters': ['query', 'history']
}

manager.save_prompt_template(
    template_id='vpc_troubleshooting',
    template=template,
    version='1.0.0'
)
```

### Version Control

All prompts are:
- Stored in S3 with versioning enabled
- Tracked in DynamoDB with metadata
- Logged in CloudTrail for audit

## 📈 Feedback and Improvement

### Collecting Feedback

```python
from app.feedback_collector import FeedbackCollector

collector = FeedbackCollector(
    dynamodb_table='feedback-table',
    region='us-east-1'
)

# Explicit feedback
collector.collect_feedback(
    session_id='session-123',
    interaction_id='interaction-456',
    feedback_type='thumbs_up',
    rating=5,
    comments='Very helpful!'
)
```

### Analyzing Feedback

Feedback is automatically analyzed hourly (configurable) and provides:
- Satisfaction rates by template and intent
- Common complaint themes
- Recommendations for prompt improvements

## 🔐 Security Best Practices

1. **Enable CloudTrail**: Track all API calls for audit
2. **Use IAM Roles**: Never hardcode credentials
3. **Enable Encryption**: All data encrypted at rest and in transit
4. **Implement Rate Limiting**: API Gateway throttling enabled
5. **Monitor for Anomalies**: CloudWatch alarms configured
6. **Regular Security Audits**: Review guardrail logs

## 💰 Cost Optimization

- **DynamoDB**: On-demand billing with TTL for old conversations
- **Lambda**: Right-sized memory and timeout configurations
- **S3**: Lifecycle policies for archiving old versions
- **API Gateway**: Usage plans and throttling
- **CloudWatch**: Optimized log retention periods

Estimated monthly cost for moderate usage (1000 queries/day):
- Lambda: $10-20
- DynamoDB: $5-15
- Bedrock: $50-100 (based on Claude 3 Sonnet pricing)
- Other services: $5-10
- **Total**: ~$70-145/month

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 Project Structure

```
01_1.5_customer_support_ai_assistant/
├── app/                          # Core application modules
│   ├── bedrock_prompt_manager.py
│   ├── guardrails_manager.py
│   ├── conversation_handler.py
│   ├── intent_detector.py
│   ├── quality_validator.py
│   └── feedback_collector.py
├── iac/                          # Infrastructure as Code
│   ├── api_gateway.tf
│   ├── dynamodb.tf
│   ├── lambda.tf
│   ├── step_functions.tf
│   ├── monitoring.tf
│   └── ...
├── tests/                        # Test suite
│   ├── test_intent_detector.py
│   ├── test_quality_validator.py
│   ├── test_guardrails.py
│   └── ...
├── lambda_*.py                   # Lambda function handlers
├── step_functions_workflow.json  # Step Functions definition
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🎓 Learning Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [AWS Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/best-practices.html)
- [Responsible AI Guidelines](https://aws.amazon.com/machine-learning/responsible-ai/)

## 📄 License

This project is provided as-is for educational purposes.

## 🙏 Acknowledgments

Built as part of the AWS Generative AI Professional Certification bonus assignment.

---

**⚠️ Important**: This is a demonstration project. Before using in production:
- Conduct thorough security review
- Perform load testing
- Implement authentication and authorization
- Add comprehensive error handling
- Set up proper monitoring and alerting
- Review and adjust costs

## 🆘 Support

For issues or questions:
1. Check the documentation in `/docs`
2. Review CloudWatch logs for errors
3. Consult the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide
4. Open an issue in the repository

---

**Built with ❤️ using AWS Serverless Services and Amazon Bedrock**



