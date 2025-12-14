# OpenSearch Permission Fix

## Problem
Lambda can't write to OpenSearch: `AuthorizationException(403, 'security_exception', 'no permissions for [indices:data/write/index]')`

## Root Cause
OpenSearch has Fine-Grained Access Control (FGAC) enabled. The Lambda IAM role has permission at AWS level, but OpenSearch's internal security needs role mapping.

---

## Solution Option 1: Configure OpenSearch Role Mapping (Recommended)

Map the Lambda IAM role to OpenSearch permissions via AWS Console or API.

### Step 1: Access OpenSearch Dashboards

```bash
# Get OpenSearch endpoint and credentials
cd ~/build-on-aws-genai-pro/enterprise_genai_knowledge_assistant/iac
terraform output opensearch_dashboard_endpoint
terraform output -raw opensearch_password_secret_arn | xargs -I {} aws secretsmanager get-secret-value --secret-id {} --query SecretString --output text | jq -r '.password'
```

### Step 2: Configure Role Mapping

1. Open OpenSearch Dashboards URL (from terraform output)
2. Login with username: `admin` and password from above
3. Go to: **Security** → **Roles** → **all_access**
4. Click **Mapped users** tab
5. Click **Map users**
6. Under **Backend roles**, add:
   ```
   arn:aws:iam::284244381060:role/gka-lambda-execution-role
   ```
7. Click **Map**

### Step 3: Test

```bash
curl -X POST https://3chov1t2di.execute-api.us-east-1.amazonaws.com/prod/documents \
  -H "Content-Type: application/json" \
  -d '{
    "document_key": "public/uploads/anche.raja@gmail.com/1765671130739-Resume-Raja.pdf",
    "document_type": "pdf"
  }'
```

---

## Solution Option 2: Use Master User Credentials (Quick Fix)

Update Lambda to use the master user credentials instead of IAM auth.

### Update document_processor Lambda:

Add at the top of `get_opensearch_client()` function:

```python
def get_opensearch_client():
    """Get OpenSearch client with proper auth"""
    # Get credentials from Secrets Manager
    secrets_client = boto3.client('secretsmanager')
    secret_response = secrets_client.get_secret_value(
        SecretId=os.environ.get('OPENSEARCH_SECRET')
    )
    credentials = json.loads(secret_response['SecretString'])
    
    # Use HTTP Basic Auth with master credentials
    from requests.auth import HTTPBasicAuth
    auth = HTTPBasicAuth(credentials['username'], credentials['password'])
    
    client = OpenSearch(
        hosts=[{'host': OPENSEARCH_DOMAIN, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    return client
```

Then rebuild and redeploy Lambda:

```bash
cd ~/build-on-aws-genai-pro/enterprise_genai_knowledge_assistant
./build-lambda.sh
cd lambda/document_processor/package
zip -r ../deploy.zip .
aws lambda update-function-code \
  --function-name gka-document-processor \
  --zip-file fileb://../deploy.zip
```

---

## Solution Option 3: Disable Fine-Grained Access Control (Less Secure)

Simplify to IAM-only auth by disabling FGAC.

⚠️ **Not recommended for production** - less granular control.

Update `iac/opensearch.tf`:

```hcl
advanced_security_options {
  enabled = false
}
```

Then:

```bash
cd iac
terraform apply
```

**Note:** This will recreate the OpenSearch domain (destructive operation, all data lost).

---

## Quick Command Reference

```bash
# Check Lambda logs
aws logs tail /aws/lambda/gka-document-processor --follow

# Check OpenSearch cluster health
OPENSEARCH_ENDPOINT=$(cd iac && terraform output -raw opensearch_endpoint)
SECRET_ARN=$(cd iac && terraform output -raw opensearch_password_secret_arn)
CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text)
USERNAME=$(echo $CREDENTIALS | jq -r .username)
PASSWORD=$(echo $CREDENTIALS | jq -r .password)

curl -u $USERNAME:$PASSWORD "https://$OPENSEARCH_ENDPOINT/_cluster/health"

# Test index creation manually
curl -u $USERNAME:$PASSWORD -X PUT "https://$OPENSEARCH_ENDPOINT/document-chunks" \
  -H 'Content-Type: application/json' \
  -d '{
    "mappings": {
      "properties": {
        "content": {"type": "text"},
        "embedding": {"type": "knn_vector", "dimension": 1536},
        "metadata": {"type": "object"}
      }
    },
    "settings": {
      "index": {
        "knn": true
      }
    }
  }'
```

---

## Recommended Approach

**For this demo environment:** Use Solution Option 1 (Role Mapping) - it's secure and preserves fine-grained access control.

**Steps:**
1. Access OpenSearch Dashboards
2. Map Lambda IAM role to `all_access` role
3. Test document upload
4. Verify data in OpenSearch

This allows Lambda to write while maintaining security.

---

**Status:** Ready to fix
**Impact:** Medium (currently blocking document indexing)
**Time:** 5 minutes for role mapping

Last Updated: December 14, 2025
