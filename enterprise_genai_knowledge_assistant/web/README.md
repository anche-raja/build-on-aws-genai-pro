# GenAI Knowledge Assistant - Web Interface

React-based web interface for the GenAI Knowledge Assistant with AWS Amplify integration.

## Features

- 🔐 **AWS Cognito Authentication** - Secure user authentication and authorization
- 💬 **Interactive Chat Interface** - Real-time conversation with AI assistant
- 👍 **Feedback Collection** - Thumbs up/down and detailed ratings
- 📊 **Admin Dashboard** - Real-time metrics and analytics
- 📄 **Document Upload** - Upload and manage knowledge base documents
- 📈 **Quality Metrics** - View response quality scores in real-time
- 🎨 **Material-UI Design** - Modern, responsive interface

## Prerequisites

- Node.js >= 18.x
- npm or yarn
- AWS account with Cognito configured
- API Gateway endpoint URL

## Installation

```bash
cd web
npm install
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Update `.env` with your Terraform outputs:
```bash
# From terraform output
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=<terraform output cognito_user_pool_id>
REACT_APP_USER_POOL_CLIENT_ID=<terraform output cognito_user_pool_client_id>
REACT_APP_IDENTITY_POOL_ID=<terraform output cognito_identity_pool_id>
REACT_APP_COGNITO_DOMAIN=<terraform output cognito_domain>
REACT_APP_API_ENDPOINT=<terraform output api_url>
REACT_APP_REDIRECT_SIGN_IN=http://localhost:3000
REACT_APP_REDIRECT_SIGN_OUT=http://localhost:3000
```

## Development

Run the development server:
```bash
npm start
```

The app will open at http://localhost:3000

## Build

Build for production:
```bash
npm run build
```

The build files will be in the `build/` directory.

## Deploy to S3

1. Build the app:
```bash
npm run build
```

2. Deploy to S3:
```bash
aws s3 sync build/ s3://<your-s3-bucket>/ --delete
```

3. Invalidate CloudFront cache:
```bash
aws cloudfront create-invalidation \
  --distribution-id <your-distribution-id> \
  --paths "/*"
```

## Project Structure

```
web/
├── public/           # Static assets
├── src/
│   ├── components/   # Reusable components
│   │   ├── Layout.js
│   │   └── FeedbackDialog.js
│   ├── pages/        # Page components
│   │   ├── Chat.js
│   │   ├── AdminDashboard.js
│   │   ├── DocumentUpload.js
│   │   ├── Analytics.js
│   │   └── Settings.js
│   ├── aws-exports.js    # AWS configuration
│   ├── App.js            # Main app component
│   ├── index.js          # Entry point
│   └── index.css         # Global styles
├── package.json
└── README.md
```

## Components

### Chat Interface (`pages/Chat.js`)
- Real-time conversation with AI
- Message history
- Markdown rendering
- Quality scores display
- Thumbs up/down feedback
- Detailed feedback dialog

### Admin Dashboard (`pages/AdminDashboard.js`)
- Summary metrics cards
- Query trend charts
- Model usage distribution
- Quality scores visualization
- Recent feedback display
- Governance metrics

### Document Upload (`pages/DocumentUpload.js`)
- File upload interface
- Document type selection
- Upload progress tracking
- Document management

### Feedback Dialog (`components/FeedbackDialog.js`)
- Star rating (1-5)
- Comment textarea
- Quality metrics display
- Success/error handling

## Authentication

The app uses AWS Amplify's `Authenticator` component which provides:
- Sign up
- Sign in
- Forgot password
- Change password
- MFA (if enabled)

Users must be authenticated to access the app.

## API Integration

The app integrates with your API Gateway endpoints:
- `POST /query` - Send chat messages
- `POST /feedback` - Submit user feedback
- `POST /documents` - Upload documents

All API calls are authenticated using Cognito credentials.

## Customization

### Theme

Edit `src/App.js` to customize the Material-UI theme:
```javascript
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',  // Change primary color
    },
  },
});
```

### Add Pages

1. Create a new page component in `src/pages/`
2. Add route in `src/App.js`
3. Add menu item in `src/components/Layout.js`

## Troubleshooting

### Authentication Issues
- Verify Cognito configuration in `.env`
- Check user pool and client ID
- Ensure redirect URLs match

### API Connection Issues
- Verify API endpoint URL
- Check CORS configuration on API Gateway
- Ensure user has permissions to invoke API

### Build Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear cache: `npm cache clean --force`

## Production Checklist

- [ ] Update `.env` with production values
- [ ] Enable HTTPS redirect URLs in Cognito
- [ ] Configure custom domain for CloudFront
- [ ] Enable CloudFront compression
- [ ] Set up monitoring and alerts
- [ ] Configure CSP headers
- [ ] Enable CloudFront access logs
- [ ] Test authentication flow
- [ ] Test all API integrations
- [ ] Perform security audit

## License

See main project LICENSE file.

