// AWS Amplify Configuration
// Replace these values with your Terraform outputs

const awsconfig = {
  Auth: {
    Cognito: {
      region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
      userPoolId: process.env.REACT_APP_USER_POOL_ID || '',
      userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || '',
      identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID || '',
      loginWith: {
        oauth: {
          domain: process.env.REACT_APP_COGNITO_DOMAIN || '',
          scopes: ['email', 'openid', 'profile'],
          redirectSignIn: [process.env.REACT_APP_REDIRECT_SIGN_IN || 'http://localhost:3000'],
          redirectSignOut: [process.env.REACT_APP_REDIRECT_SIGN_OUT || 'http://localhost:3000'],
          responseType: 'code'
        }
      }
    }
  },
  Storage: {
    S3: {
      bucket: process.env.REACT_APP_DOCUMENTS_BUCKET || 'gka-documents-284244381060',
      region: process.env.REACT_APP_AWS_REGION || 'us-east-1'
    }
  },
  API: {
    REST: {
      GenAIAPI: {
        endpoint: process.env.REACT_APP_API_ENDPOINT || '',
        region: process.env.REACT_APP_AWS_REGION || 'us-east-1'
      }
    }
  }
};

export default awsconfig;

