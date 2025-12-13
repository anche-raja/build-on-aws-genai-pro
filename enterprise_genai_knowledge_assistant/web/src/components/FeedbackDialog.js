import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Rating,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { post } from 'aws-amplify/api';

export default function FeedbackDialog({ open, message, onClose, user }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!message?.request_id) return;

    setSubmitting(true);
    setError(null);

    try {
      await post({
        apiName: 'GenAIAPI',
        path: '/feedback',
        options: {
          body: {
            request_id: message.request_id,
            user_id: user?.signInDetails?.loginId || 'anonymous',
            feedback_type: 'rating',
            rating: rating,
            comment: comment.trim() || undefined,
          },
        },
      });

      setSuccess(true);
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError('Failed to submit feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setRating(0);
    setComment('');
    setSuccess(false);
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Provide Detailed Feedback</DialogTitle>
      <DialogContent>
        {success ? (
          <Alert severity="success">
            Thank you for your feedback!
          </Alert>
        ) : (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                How would you rate this response?
              </Typography>
              <Rating
                value={rating}
                onChange={(event, newValue) => setRating(newValue)}
                size="large"
              />
            </Box>

            <TextField
              fullWidth
              multiline
              rows={4}
              label="Additional Comments (optional)"
              placeholder="Tell us what was good or what could be improved..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              disabled={submitting}
            />

            {message?.quality_scores && (
              <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  Quality Metrics:
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, mt: 1 }}>
                  <Typography variant="caption">
                    Relevance: {(message.quality_scores.relevance * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="caption">
                    Coherence: {(message.quality_scores.coherence * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="caption">
                    Completeness: {(message.quality_scores.completeness * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="caption">
                    Accuracy: {(message.quality_scores.accuracy * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={rating === 0 || submitting || success}
        >
          {submitting ? 'Submitting...' : 'Submit Feedback'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

