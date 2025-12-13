# Prompt Management Guide

This guide explains how to manage, version, and optimize prompt templates for the Customer Support AI Assistant.

## Table of Contents

1. [Prompt Architecture](#prompt-architecture)
2. [Creating Prompts](#creating-prompts)
3. [Version Control](#version-control)
4. [Testing Prompts](#testing-prompts)
5. [Deployment Workflow](#deployment-workflow)
6. [Optimization Strategies](#optimization-strategies)
7. [Best Practices](#best-practices)

## Prompt Architecture

### Prompt Structure

Each prompt template consists of:

1. **Base Persona**: Defines the assistant's role and behavior
2. **Context Section**: Specific focus area (EC2, S3, Lambda, etc.)
3. **Input Variables**: Parameterized sections (`{query}`, `{history}`)
4. **Output Format**: Guidelines for response structure
5. **Metadata**: Version, category, performance metrics

### Built-in Templates

The system includes these pre-configured templates:

- `ec2_troubleshooting`: EC2 instance issues
- `s3_troubleshooting`: S3 storage and permissions
- `lambda_troubleshooting`: Lambda function issues
- `general_support`: Generic AWS support
- `fallback`: Error handling template

## Creating Prompts

### Method 1: Using Python API

```python
from app.bedrock_prompt_manager import BedrockPromptManager

# Initialize manager
manager = BedrockPromptManager(
    region='us-east-1',
    s3_bucket='your-prompt-bucket',
    dynamodb_table='your-prompt-table'
)

# Define template
template = {
    'name': 'RDS Database Troubleshooting',
    'template': '''You are an expert AWS Customer Support specialist helping with RDS database issues.

SPECIFIC FOCUS: RDS Database Troubleshooting

When helping with RDS issues:
1. Identify the database engine (MySQL, PostgreSQL, Aurora, etc.)
2. Check connection strings and security groups
3. Review RDS events and logs
4. Verify parameter groups and options groups
5. Check for backup and maintenance windows

Common RDS issues to investigate:
- Connection timeouts
- Slow query performance
- Storage issues
- Backup failures
- Replication lag

User Query: {query}
Conversation History: {history}

Please provide a structured troubleshooting response.''',
    'parameters': ['query', 'history']
}

# Save template
manager.save_prompt_template(
    template_id='rds_troubleshooting',
    template=template,
    version='1.0.0',
    metadata={
        'author': 'your-name',
        'category': 'database',
        'approved': True,
        'approved_by': 'manager-name',
        'approved_date': '2024-01-15'
    }
)

print("Template saved successfully!")
```

### Method 2: Direct S3 Upload

```bash
# Create template JSON file
cat > rds_template.json << 'EOF'
{
  "name": "RDS Database Troubleshooting",
  "template": "You are an expert AWS Customer Support specialist...",
  "parameters": ["query", "history"]
}
EOF

# Upload to S3
aws s3 cp rds_template.json \
  s3://your-prompt-bucket/prompts/rds_troubleshooting/1.0.0.json

# Update DynamoDB metadata
aws dynamodb put-item \
  --table-name your-prompt-table \
  --item '{
    "template_id": {"S": "rds_troubleshooting"},
    "version": {"S": "1.0.0"},
    "s3_key": {"S": "prompts/rds_troubleshooting/1.0.0.json"},
    "created_at": {"S": "2024-01-15T10:00:00Z"}
  }'
```

## Version Control

### Versioning Strategy

Use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes to template structure
- **MINOR**: New features or significant improvements
- **PATCH**: Bug fixes or minor tweaks

### Version History

```python
# List all versions of a template
manager = BedrockPromptManager(...)
versions = manager.list_prompt_templates()

for template in versions:
    if template['template_id'] == 'ec2_troubleshooting':
        print(f"Version: {template['version']}, Created: {template['created_at']}")
```

### Rollback

```python
# Rollback to previous version
manager.save_prompt_template(
    template_id='ec2_troubleshooting',
    template=old_template,
    version='1.0.1',
    metadata={'rollback_from': '1.1.0', 'reason': 'Performance issues'}
)
```

## Testing Prompts

### Local Testing

```python
# Test prompt locally before deployment
from app.bedrock_prompt_manager import BedrockPromptManager

manager = BedrockPromptManager(region='us-east-1')

# Get template
template = manager.get_prompt_template('ec2_troubleshooting')

# Format with test data
formatted_prompt = manager.format_prompt(
    template=template,
    parameters={
        'query': 'My EC2 instance is not responding',
        'history': 'No previous conversation'
    }
)

# Test with Bedrock
response = manager.invoke_model(
    prompt=formatted_prompt,
    model_id='anthropic.claude-3-sonnet-20240229-v1:0'
)

print("Response:", response['content'])
```

### A/B Testing

```python
# Compare two prompt versions
def compare_prompts(query, version_a, version_b):
    manager = BedrockPromptManager(...)
    
    # Test version A
    template_a = manager.get_prompt_template('ec2_troubleshooting', version_a)
    response_a = test_prompt(template_a, query)
    
    # Test version B
    template_b = manager.get_prompt_template('ec2_troubleshooting', version_b)
    response_b = test_prompt(template_b, query)
    
    # Compare results
    return {
        'version_a': {'response': response_a, 'version': version_a},
        'version_b': {'response': response_b, 'version': version_b}
    }

results = compare_prompts(
    query='My EC2 instance is not responding',
    version_a='1.0.0',
    version_b='1.1.0'
)
```

### Automated Testing

Create test cases in `tests/test_prompts.py`:

```python
import pytest
from app.bedrock_prompt_manager import BedrockPromptManager
from app.quality_validator import QualityValidator

@pytest.fixture
def prompt_manager():
    return BedrockPromptManager(region='us-east-1')

@pytest.fixture
def quality_validator():
    return QualityValidator()

def test_ec2_prompt_quality(prompt_manager, quality_validator):
    """Test EC2 troubleshooting prompt produces high-quality responses."""
    
    test_cases = [
        {
            'query': 'EC2 instance not responding to SSH',
            'min_quality_score': 75,
            'required_keywords': ['security group', 'status checks', 'SSH']
        },
        {
            'query': 'Instance status check failed',
            'min_quality_score': 75,
            'required_keywords': ['status checks', 'system log', 'reboot']
        }
    ]
    
    template = prompt_manager.get_prompt_template('ec2_troubleshooting')
    
    for test_case in test_cases:
        # Generate response
        formatted_prompt = prompt_manager.format_prompt(
            template=template,
            parameters={'query': test_case['query'], 'history': ''}
        )
        
        response = prompt_manager.invoke_model(formatted_prompt)
        
        # Validate quality
        validation = quality_validator.validate_response(
            response=response['content'],
            query=test_case['query'],
            intent='ec2_troubleshooting'
        )
        
        # Assert quality
        assert validation['score'] >= test_case['min_quality_score'], \
            f"Quality score {validation['score']} below threshold"
        
        # Check required keywords
        response_lower = response['content'].lower()
        for keyword in test_case['required_keywords']:
            assert keyword.lower() in response_lower, \
                f"Missing required keyword: {keyword}"
```

## Deployment Workflow

### 1. Development

```bash
# Work on prompt locally
# Test with sample queries
# Validate quality scores
```

### 2. Staging

```bash
# Deploy to staging environment
python scripts/deploy_prompt.py \
  --template-id ec2_troubleshooting \
  --version 1.1.0 \
  --environment staging

# Run automated tests
pytest tests/test_prompts.py -v

# Manual testing
```

### 3. Production Deployment

```bash
# Deploy to production with approval
python scripts/deploy_prompt.py \
  --template-id ec2_troubleshooting \
  --version 1.1.0 \
  --environment production \
  --approved-by manager@example.com

# Monitor for issues
# Check quality metrics
# Review feedback
```

### 4. Monitoring

```bash
# Monitor prompt performance
aws cloudwatch get-metric-statistics \
  --namespace CustomerSupportAI \
  --metric-name QualityScore \
  --dimensions Name=TemplateId,Value=ec2_troubleshooting \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-16T00:00:00Z \
  --period 3600 \
  --statistics Average
```

## Optimization Strategies

### 1. Analyze Feedback

```python
from app.feedback_collector import FeedbackCollector

collector = FeedbackCollector(
    dynamodb_table='feedback-table',
    region='us-east-1'
)

# Analyze feedback for specific template
analysis = collector.analyze_feedback(
    time_range_hours=168,  # Last week
    template_id='ec2_troubleshooting'
)

print(f"Satisfaction rate: {analysis['statistics']['satisfaction_rate']}%")
print(f"Average rating: {analysis['statistics']['average_rating']}")
print(f"Issues identified: {analysis['issues']}")
print(f"Recommendations: {analysis['recommendations']}")
```

### 2. Identify Improvement Areas

Common issues to address:

- **Too technical**: Simplify language, add explanations
- **Not specific enough**: Add more concrete examples
- **Missing steps**: Include comprehensive troubleshooting steps
- **Wrong tone**: Adjust for more empathy or professionalism
- **Outdated information**: Update with latest AWS features

### 3. Iterative Refinement

```python
# Example: Refining based on feedback

# Original prompt (v1.0.0)
original = """Check the EC2 instance status and security groups."""

# Improved prompt (v1.1.0) - More specific and empathetic
improved = """I understand you're experiencing issues with your EC2 instance not responding. Let's troubleshoot this together.

Here are the specific steps to diagnose the issue:

1. **Check Instance Status Checks**:
   - Go to the EC2 Console
   - Select your instance
   - Look at the Status Checks tab
   - Note if there are any failed system or instance checks

2. **Verify Security Group Rules**:
   - Check that port 22 (for SSH) or 3389 (for RDP) is open
   - Ensure your current IP address is allowed in the inbound rules
   - Verify the security group is attached to your instance

3. **Review Network Configuration**:
   - Confirm the instance has a public IP address (if accessing from internet)
   - Check that the route table allows internet gateway access
   - Verify Network ACLs aren't blocking traffic

4. **Check System Logs**:
   - Right-click instance → Instance Settings → Get System Log
   - Look for any boot errors or network issues

Would you like me to help you with any specific step?"""
```

### 4. Prompt Engineering Techniques

#### Chain-of-Thought

```python
template = """Before providing your answer, think through these steps:
1. What AWS service is the user asking about?
2. What is the specific problem they're experiencing?
3. What are the most likely causes?
4. What troubleshooting steps would help?

Now provide your structured response..."""
```

#### Few-Shot Examples

```python
template = """Here are examples of good responses:

Example 1:
User: "My instance won't start"
Response: "I understand your EC2 instance isn't starting. Let's check: 1) Instance status 2) EBS volumes 3) Limits..."

Example 2:
User: "S3 access denied"
Response: "I see you're getting access denied errors with S3. Let's verify: 1) Bucket policy 2) IAM permissions 3) CORS..."

Now help this user:
{query}"""
```

#### Structured Output

```python
template = """Provide your response in this format:

## Acknowledgment
[Acknowledge the user's issue]

## Diagnostic Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Next Steps
[What the user should do next]

## Additional Resources
[Relevant AWS documentation]

User Query: {query}"""
```

## Best Practices

### 1. Clarity and Specificity

✅ **Good**: "Check if port 22 is open in your security group's inbound rules"

❌ **Bad**: "Check your security settings"

### 2. Structured Responses

Always include:
- Acknowledgment
- Clear steps
- Expected outcomes
- Next actions

### 3. Safety and Boundaries

Never allow prompts to:
- Provide credentials
- Make future commitments
- Perform account modifications
- Disparage competitors

### 4. Continuous Monitoring

Track:
- Quality scores
- User satisfaction
- Response time
- Error rates

### 5. Documentation

Document each prompt version:
- Purpose and use case
- Changes from previous version
- Expected quality metrics
- Known limitations

## Example: Complete Prompt Lifecycle

```python
# 1. Create new prompt
template = create_prompt_template('dynamodb_troubleshooting', 'v1.0.0')

# 2. Test locally
test_results = run_local_tests(template)
assert test_results['avg_quality_score'] > 75

# 3. Deploy to staging
deploy_to_staging(template)

# 4. Monitor for 1 week
metrics = monitor_performance(days=7)

# 5. Analyze feedback
feedback = analyze_feedback(template_id='dynamodb_troubleshooting')

# 6. If successful, deploy to production
if feedback['satisfaction_rate'] > 85:
    deploy_to_production(template)
    
# 7. Continue monitoring
schedule_monitoring(template_id='dynamodb_troubleshooting')
```

## Troubleshooting

### Low Quality Scores

- Review failed validation criteria
- Check if response is too short/long
- Verify all required elements are present
- Test with different queries

### Low User Satisfaction

- Analyze user comments
- Check for tone issues
- Verify technical accuracy
- Test for clarity and specificity

### High Regeneration Rate

- Check if initial responses are incomplete
- Review quality validation thresholds
- Verify prompt provides sufficient guidance

## Resources

- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [AWS Bedrock Best Practices](https://docs.aws.amazon.com/bedrock/)
- [Prompt Library Examples](sample-data/example_prompts.json)

---

**Remember**: Good prompts are iterative. Start simple, gather feedback, and refine continuously.



