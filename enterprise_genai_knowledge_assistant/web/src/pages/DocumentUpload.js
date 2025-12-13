import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Grid,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as DocIcon,
  Delete as DeleteIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { post } from 'aws-amplify/api';

export default function DocumentUpload({ user }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [documentType, setDocumentType] = useState('text');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [uploadedDocs, setUploadedDocs] = useState([]);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    setSuccess(false);
    setError(null);
    
    // Auto-detect file type
    if (file) {
      const ext = file.name.split('.').pop().toLowerCase();
      if (ext === 'pdf') {
        setDocumentType('pdf');
      } else {
        setDocumentType('text');
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // In a real implementation, you would:
      // 1. Upload file to S3
      // 2. Call the document processor API

      const reader = new FileReader();
      reader.onload = async (e) => {
        const content = e.target.result;

        // Call document processor API
        await post({
          apiName: 'GenAIAPI',
          path: '/documents',
          options: {
            body: {
              document_key: `uploads/${user?.signInDetails?.loginId}/${selectedFile.name}`,
              document_type: documentType,
              // In production, you'd upload to S3 first and pass the key
            },
          },
        });

        clearInterval(progressInterval);
        setUploadProgress(100);
        setSuccess(true);
        setUploadedDocs((prev) => [
          ...prev,
          {
            name: selectedFile.name,
            type: documentType,
            timestamp: new Date(),
          },
        ]);
        setTimeout(() => {
          setSelectedFile(null);
          setUploadProgress(0);
          setSuccess(false);
        }, 2000);
      };

      reader.readAsText(selectedFile);
    } catch (err) {
      console.error('Upload error:', err);
      setError('Failed to upload document. Please try again.');
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Document Upload
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 3 }}>
        Upload documents to enhance the knowledge base
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Upload New Document
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ mb: 2 }} icon={<SuccessIcon />}>
                Document uploaded successfully!
              </Alert>
            )}

            <Box sx={{ mb: 3 }}>
              <input
                accept=".txt,.pdf,.doc,.docx"
                style={{ display: 'none' }}
                id="file-upload"
                type="file"
                onChange={handleFileSelect}
                disabled={uploading}
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  fullWidth
                  startIcon={<UploadIcon />}
                  disabled={uploading}
                  sx={{ height: 56 }}
                >
                  {selectedFile ? selectedFile.name : 'Choose File'}
                </Button>
              </label>
            </Box>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Document Type</InputLabel>
              <Select
                value={documentType}
                label="Document Type"
                onChange={(e) => setDocumentType(e.target.value)}
                disabled={uploading}
              >
                <MenuItem value="text">Text Document</MenuItem>
                <MenuItem value="pdf">PDF Document</MenuItem>
              </Select>
            </FormControl>

            {uploading && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Uploading... {uploadProgress}%
                </Typography>
                <LinearProgress variant="determinate" value={uploadProgress} />
              </Box>
            )}

            <Button
              variant="contained"
              fullWidth
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              startIcon={<UploadIcon />}
            >
              {uploading ? 'Uploading...' : 'Upload Document'}
            </Button>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Uploaded Documents
            </Typography>
            {uploadedDocs.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No documents uploaded yet
              </Typography>
            ) : (
              <List>
                {uploadedDocs.map((doc, index) => (
                  <ListItem
                    key={index}
                    secondaryAction={
                      <IconButton edge="end" aria-label="delete">
                        <DeleteIcon />
                      </IconButton>
                    }
                  >
                    <ListItemIcon>
                      <DocIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary={doc.name}
                      secondary={`${doc.type} • ${doc.timestamp.toLocaleString()}`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
