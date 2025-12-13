#!/bin/bash
# Update .env with new Cognito values and rebuild/deploy the web app

echo "🔧 Creating .env file with new Cognito values..."
cat > .env <<EOF
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=us-east-1_R7F730slC
REACT_APP_USER_POOL_CLIENT_ID=489km24v70ugekj8cr5pt43u38
REACT_APP_API_ENDPOINT=https://3chov1t2di.execute-api.us-east-1.amazonaws.com/prod
EOF

echo "✅ .env file created:"
cat .env
echo ""

echo "🔨 Building React app..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    
    echo "🚀 Deploying to S3..."
    aws s3 sync build/ s3://gka-amplify-deployment-284244381060/ --delete
    
    if [ $? -eq 0 ]; then
        echo "✅ Deployment successful!"
        echo ""
        echo "🌐 Your web app is available at:"
        echo "   https://d3ck08a6xusuim.cloudfront.net"
        echo ""
        echo "🔑 Note: You need to create users in Cognito first:"
        echo "   aws cognito-idp admin-create-user \\"
        echo "     --user-pool-id us-east-1_R7F730slC \\"
        echo "     --username admin@example.com \\"
        echo "     --user-attributes Name=email,Value=admin@example.com"
    else
        echo "❌ Deployment failed!"
        exit 1
    fi
else
    echo "❌ Build failed!"
    exit 1
fi

