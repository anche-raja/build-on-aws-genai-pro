# Architecture Deep Dive

## System Architecture Overview

This document provides detailed architectural information about the RAG Vector Search System.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Client Applications                        │
│                     (Web UI, CLI, SDK, Mobile)                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTPS
                    ┌────────────▼─────────────┐
                    │   Amazon CloudFront      │
                    │   (Optional CDN)         │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   API Gateway            │
                    │   - REST API             │
                    │   - Request validation   │
                    │   - Rate limiting        │
                    │   - API keys/Auth        │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                      │
    ┌─────────▼────────┐                 ┌─────────▼────────┐
    │  Lambda: Query   │                 │  Lambda: Feedback│
    │  Processing      │                 │  Collection      │
    │  - RAG logic     │                 │  - Store ratings │
    │  - Retrieval     │                 │  - Analytics     │
    │  - Generation    │                 │                  │
    └─────────┬────────┘                 └──────────────────┘
              │
    ┌─────────┴─────────────┬─────────────────┬──────────────┐
    │                       │                 │              │
┌───▼────────┐    ┌────────▼─────┐   ┌──────▼─────┐  ┌────▼─────┐
│ Amazon     │    │ Amazon       │   │ DynamoDB   │  │ S3       │
│ Bedrock    │    │ OpenSearch   │   │ Metadata   │  │ Docs     │
│            │    │              │   │            │  │          │
│ - Claude 3 │    │ - Vectors    │   │ - Tracking │  │ - Raw    │
│ - Embeddings│   │ - k-NN       │   │ - Status   │  │ - Cache  │
└────────────┘    └──────────────┘   └────────────┘  └──────────┘
```

## Ingestion Pipeline Architecture

```
┌──────────────┐
│ Data Sources │
│ - S3 Upload  │
│ - Web Crawl  │
│ - Wiki API   │
│ - DMS        │
└──────┬───────┘
       │
       │ Trigger
       │
┌──────▼────────────────────────┐
│  EventBridge / S3 Events      │
└──────┬────────────────────────┘
       │
       │ Invoke
       │
┌──────▼─────────────────────────┐
│  Lambda: Document Processor    │
│                                │
│  1. Download from S3           │
│  2. Extract text               │
│  3. Detect format              │
│  4. Apply chunking strategy    │
│  5. Generate embeddings        │
│  6. Store metadata             │
│  7. Index to vector DB         │
└────────┬───────────────────────┘
         │
    ┌────┴────┬──────────┬────────┐
    │         │          │        │
┌───▼───┐ ┌──▼──────┐ ┌─▼─────┐ ┌▼──────┐
│Bedrock│ │OpenSearch│ │DynamoDB│ │S3     │
│Embed  │ │Index     │ │Metadata│ │Archive│
└───────┘ └──────────┘ └────────┘ └───────┘
```

## Query Processing Flow

```
1. User Query
   ↓
2. API Gateway → Lambda (RAG API)
   ↓
3. Query Enhancement
   - Query expansion
   - Conversation context
   - Metadata filters
   ↓
4. Generate Query Embedding (Bedrock)
   ↓
5. Vector Search (OpenSearch/Knowledge Base)
   - Semantic similarity
   - Metadata filtering
   - Hybrid search (optional)
   ↓
6. Context Optimization
   - Rank by relevance
   - Fit token budget
   - Deduplicate
   ↓
7. Prompt Construction
   - System prompt
   - Retrieved context
   - User query
   - Conversation history
   ↓
8. LLM Invocation (Bedrock)
   - Claude 3 / Titan
   - Streaming (optional)
   ↓
9. Response Post-Processing
   - Format response
   - Add source citations
   - Calculate metadata
   ↓
10. Return to User
```

## Data Synchronization Architecture

```
┌─────────────────────┐
│  EventBridge Rule   │
│  Scheduled Trigger  │
│  (Daily @ 2 AM)     │
└─────────┬───────────┘
          │
          │ Trigger
          │
┌─────────▼────────────────┐
│ Lambda: Sync Scheduler   │
│                          │
│ 1. Find stale documents  │
│ 2. Check S3 changes      │
│ 3. Create update batches │
│ 4. Start Step Function  │
└─────────┬────────────────┘
          │
          │ Start Execution
          │
┌─────────▼──────────────────────────────┐
│  Step Functions: Sync Workflow         │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │  Map State (Parallel Batch)     │  │
│  │  ┌──────────────────────────┐   │  │
│  │  │ Process Document 1       │   │  │
│  │  └──────────────────────────┘   │  │
│  │  ┌──────────────────────────┐   │  │
│  │  │ Process Document 2       │   │  │
│  │  └──────────────────────────┘   │  │
│  │  ┌──────────────────────────┐   │  │
│  │  │ Process Document N       │   │  │
│  │  └──────────────────────────┘   │  │
│  └─────────────────────────────────┘  │
│                                         │
│  Error Handling & Retry Logic          │
└────────────────────────────────────────┘
```

## Security Architecture

### Network Security

```
┌────────────────────────────────────┐
│          Internet                  │
└─────────────┬──────────────────────┘
              │ HTTPS only
   ┌──────────▼───────────┐
   │  AWS WAF (Optional)  │
   │  - Rate limiting     │
   │  - SQL injection     │
   │  - XSS protection    │
   └──────────┬───────────┘
              │
   ┌──────────▼──────────────┐
   │  API Gateway            │
   │  - TLS 1.2+             │
   │  - API Keys             │
   │  - Usage plans          │
   └──────────┬──────────────┘
              │
   ┌──────────▼──────────────────┐
   │  Lambda (in VPC - optional) │
   │  - Security Groups          │
   │  - Private subnets          │
   └──────────┬──────────────────┘
              │
     ┌────────┴────────┐
     │                 │
┌────▼──────┐   ┌─────▼────────┐
│ OpenSearch│   │  Bedrock     │
│ - VPC     │   │  - PrivateLink│
│ - SG      │   │  (optional)  │
│ - Encryption│ │               │
└───────────┘   └──────────────┘
```

### Data Security

```
┌─────────────────────────────────────┐
│        Encryption at Rest           │
├─────────────────────────────────────┤
│ S3: AES-256 / KMS                   │
│ DynamoDB: KMS encryption            │
│ OpenSearch: AES-256                 │
│ Secrets Manager: KMS                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│     Encryption in Transit           │
├─────────────────────────────────────┤
│ All: TLS 1.2+ (HTTPS)              │
│ API Gateway: TLS policy enforced    │
│ OpenSearch: HTTPS only              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│       Access Control                │
├─────────────────────────────────────┤
│ IAM: Least privilege roles          │
│ S3: Bucket policies                 │
│ OpenSearch: Fine-grained access     │
│ DynamoDB: IAM policies              │
└─────────────────────────────────────┘
```

## Scalability Patterns

### Horizontal Scaling

```
Component         | Scaling Strategy
------------------|---------------------------------
API Gateway       | Auto-scales (AWS managed)
Lambda            | Concurrent executions (1000+)
OpenSearch        | Add data nodes horizontally
DynamoDB          | On-demand auto-scaling
S3                | Unlimited (AWS managed)
```

### Vertical Scaling

```
Component         | Scaling Strategy
------------------|---------------------------------
OpenSearch        | Larger instance types
Lambda            | Increase memory (128MB-10GB)
```

### Caching Strategy

```
┌───────────────┐
│ Client Cache  │ ← 5 minutes
├───────────────┤
│ API Gateway   │ ← 1 minute
├───────────────┤
│ Lambda Cache  │ ← Query cache (5 min)
├───────────────┤
│ OpenSearch    │ ← Query cache
└───────────────┘
```

## High Availability Design

### Multi-AZ Deployment

```
Region: us-east-1
├── AZ: us-east-1a
│   ├── OpenSearch Node 1
│   └── Lambda (automatic)
├── AZ: us-east-1b
│   ├── OpenSearch Node 2
│   └── Lambda (automatic)
└── AZ: us-east-1c
    ├── OpenSearch Node 3
    └── Lambda (automatic)

Cross-Region:
- S3 Cross-Region Replication
- DynamoDB Global Tables (optional)
- Multi-region API Gateway (optional)
```

### Disaster Recovery

```
RTO (Recovery Time Objective): < 1 hour
RPO (Recovery Point Objective): < 15 minutes

Backup Strategy:
- OpenSearch: Automated snapshots (hourly)
- DynamoDB: Point-in-time recovery (35 days)
- S3: Versioning + Cross-region replication
- Lambda: Code in version control
```

## Monitoring Architecture

### Observability Stack

```
┌──────────────────────────────────────┐
│         CloudWatch Logs              │
│  - Lambda logs                       │
│  - API Gateway logs                  │
│  - OpenSearch logs                   │
│  - Step Functions logs               │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│      CloudWatch Metrics              │
│  - Request count                     │
│  - Latency (p50, p90, p99)          │
│  - Error rate                        │
│  - OpenSearch cluster health         │
│  - DynamoDB read/write capacity     │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│      CloudWatch Alarms               │
│  - Lambda errors > threshold         │
│  - API latency > 3s                  │
│  - OpenSearch yellow/red status      │
│  - DynamoDB throttling               │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│      SNS / Email Notifications       │
└──────────────────────────────────────┘
```

### Key Metrics

```
Application Metrics:
- Query latency (target: < 2s p95)
- Context retrieval time (target: < 500ms)
- LLM invocation time (target: < 3s)
- Error rate (target: < 0.1%)
- Cache hit rate (target: > 30%)

Infrastructure Metrics:
- Lambda concurrent executions
- OpenSearch CPU/memory usage
- DynamoDB consumed capacity
- S3 request rate
- API Gateway 4xx/5xx errors
```

## Cost Optimization Architecture

### Resource Tagging Strategy

```
All resources tagged with:
- Project: rag-vector-search
- Environment: dev/staging/prod
- CostCenter: engineering
- Owner: team-name
```

### Cost Allocation

```
Service          | Estimated %  | Optimization Strategy
-----------------|--------------|-----------------------
OpenSearch       | 70%          | Right-size instances
Bedrock API      | 15%          | Cache frequent queries
Lambda           | 5%           | Optimize memory/timeout
DynamoDB         | 4%           | Use on-demand billing
S3               | 3%           | Use Intelligent-Tiering
Other            | 3%           | Monitor and optimize
```

## Performance Optimization

### Query Optimization Path

```
1. Request → API Gateway
   └→ Caching layer (1 min TTL)

2. Lambda → Application Cache
   └→ In-memory query cache (5 min)

3. Vector Search → OpenSearch
   └→ Query result cache
   └→ Use filters to reduce search space

4. LLM Invocation → Bedrock
   └→ Optimize prompt length
   └→ Use appropriate model (Haiku for speed)

5. Response → Client
   └→ Compress large responses
```

### Embedding Optimization

```
Strategy                | Benefit
------------------------|---------------------------------
Batch embedding         | Reduce API calls by 10x
Dimension reduction     | Faster similarity search
Quantization           | Reduce storage by 4x
```

## Integration Points

### External System Integration

```
┌─────────────────────┐
│  RAG System         │
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────┬──────────────┐
    │             │          │              │
┌───▼────┐  ┌────▼───┐  ┌──▼────┐  ┌──────▼─────┐
│Webhook │  │REST API│  │SDK/CLI│  │EventBridge │
│Calls   │  │Clients │  │Python │  │Events      │
└────────┘  └────────┘  └───────┘  └────────────┘
```

### Data Source Connectors

```
Supported Sources:
├── S3 Direct Upload
├── Web Crawler
│   └── Configurable domains
├── Confluence
│   └── Spaces and pages
├── MediaWiki
│   └── Articles and categories
├── SharePoint (extensible)
└── Custom APIs (via Lambda)
```

## Technology Stack Summary

| Layer              | Technology                          |
|--------------------|-------------------------------------|
| **AI/ML**          | Amazon Bedrock (Claude 3, Titan)    |
| **Vector DB**      | Amazon OpenSearch Service           |
| **Metadata DB**    | Amazon DynamoDB                     |
| **Object Storage** | Amazon S3                           |
| **Compute**        | AWS Lambda                          |
| **Orchestration**  | AWS Step Functions                  |
| **API**            | Amazon API Gateway                  |
| **Scheduling**     | Amazon EventBridge                  |
| **Secrets**        | AWS Secrets Manager                 |
| **Monitoring**     | Amazon CloudWatch                   |
| **IaC**            | Terraform                           |
| **Language**       | Python 3.11                         |

---

For implementation details, see the [README.md](README.md) and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

