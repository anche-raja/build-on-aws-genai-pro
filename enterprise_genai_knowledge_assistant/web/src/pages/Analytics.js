import React from 'react';
import { Box, Typography } from '@mui/material';

export default function Analytics({ user }) {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Analytics
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Detailed analytics and insights (Coming soon)
      </Typography>
    </Box>
  );
}

