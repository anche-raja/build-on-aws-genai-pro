# Architecture Documentation

## System Architecture Overview

The AWS Customer Support AI Assistant is built using a serverless, event-driven architecture that prioritizes scalability, observability, and responsible AI practices.

## High-Level Architecture

```
┌─────────────┐
│   User/App  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│              API Gateway (REST API)                   │
│  - /query endpoint (Step Functions integration)       │
│  - /feedback endpoint (Lambda integration)            │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│           Step Functions State Machine                │
│  ┌─────────────────────────────────────────────────┐ │
│  │  1. CaptureUserQuery                            │ │
│  │  2. CheckGuardrailStatus                        │ │
│  │  3. DetectIntent                                │ │
│  │  4. CheckIntentClarity                          │ │
│  │  5. GenerateResponse                            │ │
│  │  6. ValidateQuality                             │ │
│  │  7. CheckQuality                                │ │
│  │  8. CollectFeedback                             │ │
│  └─────────────────────────────────────────────────┘ │
└──────┬───────────────────────────────────────────────┘
       │
       ├──────────────┬──────────────┬──────────────┬───────────────┐
       ▼              ▼              ▼              ▼               ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐
│  Lambda   │  │  Lambda   │  │  Lambda   │  │ Lambda   │  │  Lambda  │
│  Capture  │  │  Intent   │  │ Generate  │  │ Quality  │  │Feedback  │
│  Query    │  │ Detection │  │ Response  │  │Validation│  │Collection│
└─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬────┘  └─────┬────┘
      │              │              │              │             │
      ▼              ▼              ▼              │             ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐       │      ┌──────────┐
│  DynamoDB    │ │Comprehend│ │ Bedrock  │       │      │DynamoDB  │
│Conversations │ │   NLP    │ │ Claude 3 │       │      │Feedback  │
└──────────────┘ └──────────┘ └─────┬────┘       │      └──────────┘
                                    │             │
                               ┌────▼─────┐       │
                               │    S3    │       │
                               │ Prompts  │       │
                               └──────────┘       │
                                                  │
                        ┌─────────────────────────▼─────────────────┐
                        │         Monitoring & Observability        │
                        │  - CloudWatch Logs & Metrics              │
                        │  - CloudWatch Dashboard                   │
                        │  - X-Ray Tracing                          │
                        │  - CloudTrail Audit Logs                  │
                        └───────────────────────────────────────────┘
```

## Component Details

### 1. API Gateway

**Purpose**: Provides REST API endpoints for external access

**Key Features**:
- **Throttling**: Configurable burst and rate limits
- **CORS**: Enabled for web application access
- **Logging**: Full request/response logging to CloudWatch
- **Metrics**: Built-in metrics for monitoring
- **Security**: Can be enhanced with AWS IAM or Cognito

**Endpoints**:
- `POST /query`: Submit user queries (triggers Step Functions)
- `POST /feedback`: Submit explicit user feedback (invokes Lambda directly)

### 2. Step Functions State Machine

**Purpose**: Orchestrates the workflow with conditional branching and error handling

**States**:

1. **CaptureUserQuery**: Validates and stores the user query
2. **CheckGuardrailStatus**: Evaluates if guardrails were triggered
3. **DetectIntent**: Identifies the user's intent using NLP
4. **CheckIntentClarity**: Determines if clarification is needed
5. **GenerateResponse**: Creates AI response using appropriate prompt
6. **ValidateQuality**: Checks response quality against criteria
7. **CheckQuality**: Decides if regeneration is needed
8. **CollectFeedback**: Records implicit feedback metrics

**Error Handling**:
- Each state has catch blocks for graceful degradation
- Fallback responses ensure users always get a reply
- Errors are logged to CloudWatch for analysis

### 3. Lambda Functions

#### 3.1 Capture Query Lambda
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Responsibilities**:
  - Validate incoming queries
  - Create/retrieve conversation sessions
  - Apply input guardrails
  - Store user messages in conversation history

#### 3.2 Detect Intent Lambda
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Responsibilities**:
  - Analyze query using Amazon Comprehend
  - Match patterns to known intents
  - Calculate confidence scores
  - Determine if clarification or escalation is needed

#### 3.3 Generate Response Lambda
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 120 seconds
- **Responsibilities**:
  - Retrieve appropriate prompt template
  - Format prompt with query and context
  - Invoke Amazon Bedrock (Claude 3)
  - Apply output guardrails
  - Store assistant response

#### 3.4 Validate Quality Lambda
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Responsibilities**:
  - Check response completeness
  - Validate structure and formatting
  - Verify accuracy (no placeholders, valid code)
  - Assess tone appropriateness
  - Generate quality score

#### 3.5 Collect Feedback Lambda
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Responsibilities**:
  - Store explicit user feedback
  - Record implicit behavioral metrics
  - Send metrics to CloudWatch
  - Update feedback analytics

#### 3.6 Analyze Feedback Lambda
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 300 seconds
- **Responsibilities**:
  - Aggregate feedback over time windows
  - Identify patterns and issues
  - Generate improvement recommendations
  - Triggered by EventBridge on schedule

### 4. Data Storage

#### 4.1 DynamoDB Tables

**Conversations Table**:
```
Primary Key: session_id
Attributes:
  - session_id (String)
  - user_id (String)
  - created_at (String)
  - updated_at (String)
  - turn_count (Number)
  - messages (List)
  - metadata (Map)
  - ttl (Number) - Auto-expires old sessions
  
GSI: UserIdIndex (user_id, created_at)
```

**Prompts Table**:
```
Primary Key: template_id, version
Attributes:
  - template_id (String)
  - version (String)
  - s3_key (String)
  - created_at (String)
  - metadata (Map)
  
GSI: CreatedAtIndex (template_id, created_at)
```

**Feedback Table**:
```
Primary Key: feedback_id
Attributes:
  - feedback_id (String)
  - session_id (String)
  - interaction_id (String)
  - feedback_type (String)
  - rating (Number)
  - comments (String)
  - metadata (Map)
  - timestamp (String)
  
GSI: SessionIdIndex (session_id, timestamp)
GSI: TimestampIndex (timestamp)
Stream: Enabled for real-time processing
```

#### 4.2 S3 Buckets

**Prompt Templates Bucket**:
- **Purpose**: Store prompt template definitions
- **Versioning**: Enabled
- **Encryption**: AES-256
- **Lifecycle**: Archive old versions to Glacier after 90 days
- **Structure**: `prompts/{template_id}/{version}.json`

**Lambda Deployments Bucket**:
- **Purpose**: Store Lambda deployment packages
- **Versioning**: Enabled
- **Encryption**: AES-256

**CloudTrail Logs Bucket**:
- **Purpose**: Store audit logs
- **Versioning**: Enabled
- **Lifecycle**: Archive to Glacier after 90 days

### 5. AI/ML Services

#### 5.1 Amazon Bedrock
- **Model**: Claude 3 Sonnet (anthropic.claude-3-sonnet-20240229-v1:0)
- **Usage**: Generate customer support responses
- **Configuration**:
  - Temperature: 0.7 (balanced creativity/consistency)
  - Max tokens: 2048
  - Top-p: 0.9

#### 5.2 Amazon Comprehend
- **Services Used**:
  - Entity Detection
  - Key Phrase Extraction
  - Sentiment Analysis
- **Purpose**: Enhance intent detection and understand user emotions

### 6. Monitoring and Observability

#### 6.1 CloudWatch
- **Logs**: All Lambda and Step Functions executions
- **Metrics**: Custom metrics for feedback, quality scores, confidence
- **Dashboard**: Pre-configured dashboard with key metrics
- **Alarms**: Automated alerts for errors and performance issues

#### 6.2 AWS X-Ray
- **Tracing**: End-to-end request tracing
- **Service Map**: Visualize component interactions
- **Performance**: Identify bottlenecks

#### 6.3 CloudTrail
- **Audit Logging**: All API calls tracked
- **Data Events**: Lambda invocations, DynamoDB access, S3 operations
- **Compliance**: Meet audit requirements

## Data Flow

### Typical Query Flow

1. **User submits query** → API Gateway
2. **API Gateway** → Triggers Step Functions execution
3. **Step Functions** → Invokes Capture Query Lambda
4. **Capture Query**:
   - Validates query
   - Creates/retrieves session from DynamoDB
   - Checks input guardrails
   - Returns session info
5. **Step Functions** → Invokes Detect Intent Lambda
6. **Detect Intent**:
   - Analyzes with Comprehend
   - Matches intent patterns
   - Returns intent + confidence
7. **Step Functions** → Decision: Clarification needed?
   - If yes → Generate clarification question
   - If no → Continue to response generation
8. **Generate Response**:
   - Retrieves prompt template from S3/DynamoDB
   - Formats with context
   - Invokes Bedrock
   - Checks output guardrails
   - Stores response in DynamoDB
9. **Validate Quality**:
   - Runs quality checks
   - Returns quality score
10. **Step Functions** → Decision: Quality acceptable?
    - If no → Regenerate with different approach
    - If yes → Continue
11. **Collect Feedback**:
    - Records implicit metrics
    - Stores in DynamoDB Feedback table
12. **Step Functions** → Returns final response to API Gateway
13. **API Gateway** → Returns response to user

## Security Architecture

### Defense in Depth

1. **Network Layer**:
   - API Gateway with throttling
   - VPC endpoints for AWS services (optional)

2. **Application Layer**:
   - Input validation
   - Guardrails for sensitive content
   - Output validation

3. **Data Layer**:
   - Encryption at rest (all storage)
   - Encryption in transit (TLS)
   - DynamoDB TTL for data retention

4. **Access Control**:
   - IAM roles with least privilege
   - Resource-based policies
   - CloudTrail for audit

### Guardrails Implementation

```
Input Query
    ↓
[Pattern Matching]
    ├─ AWS Access Keys → BLOCK
    ├─ Passwords → BLOCK
    ├─ Private Keys → BLOCK
    └─ Safe → Continue
         ↓
[Topic Detection]
    ├─ Future Features → BLOCK
    ├─ Credentials Request → BLOCK
    └─ Safe → Continue
         ↓
[Process Query]
         ↓
[Output Validation]
    ├─ Sensitive Data → BLOCK
    ├─ Future Commitments → BLOCK
    ├─ Competitor Disparagement → BLOCK
    └─ Safe → Return to User
```

## Scalability Considerations

### Horizontal Scaling
- **Lambda**: Auto-scales with concurrent executions
- **DynamoDB**: On-demand capacity mode
- **API Gateway**: Handles thousands of requests/second
- **Step Functions**: 1M+ concurrent executions

### Performance Optimization
- **DynamoDB GSIs**: Optimized query patterns
- **Lambda Memory**: Right-sized for performance
- **Connection Pooling**: Reuse AWS service clients
- **Caching**: Consider ElastiCache for frequently accessed prompts

### Cost Optimization
- **DynamoDB TTL**: Auto-expire old data
- **S3 Lifecycle**: Archive to cheaper storage tiers
- **Lambda**: Efficient memory allocation
- **CloudWatch**: Optimized log retention

## Disaster Recovery

### Backup Strategy
- **DynamoDB**: Point-in-time recovery enabled
- **S3**: Versioning and cross-region replication (optional)
- **Infrastructure**: Terraform state in version control

### Recovery Procedures
- **RPO**: < 5 minutes (DynamoDB PITR)
- **RTO**: < 1 hour (Terraform redeploy)

## Future Enhancements

1. **Multi-Region Deployment**: Active-active for global scale
2. **Advanced Analytics**: Amazon QuickSight dashboards
3. **Voice Integration**: Amazon Transcribe + Polly
4. **Knowledge Base**: Amazon Kendra integration
5. **A/B Testing**: Multiple prompt variants
6. **Reinforcement Learning**: RLHF for continuous improvement

## Design Decisions

### Why Step Functions?
- Visual workflow representation
- Built-in error handling and retries
- Easy conditional branching
- CloudWatch integration
- Audit trail

### Why Claude 3 Sonnet?
- Strong instruction following
- Good balance of speed and quality
- Appropriate context window (200K tokens)
- Cost-effective for production use

### Why DynamoDB?
- Serverless (no management)
- Flexible schema for evolving data
- Built-in TTL for data expiration
- Global tables for multi-region
- Streams for real-time processing

### Why Separate Validation Step?
- Allows for quality-based regeneration
- Tracks quality metrics over time
- Enables continuous improvement
- Catches issues before user sees them

## Conclusion

This architecture provides a robust, scalable, and maintainable foundation for an AI-powered customer support system. The serverless approach minimizes operational overhead while the comprehensive guardrails and quality checks ensure responsible AI deployment.
