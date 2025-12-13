import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Switch,
  FormControlLabel,
  Divider,
  Button,
} from '@mui/material';

export default function Settings({ user }) {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 3 }}>
        Manage your preferences
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          User Preferences
        </Typography>
        <Divider sx={{ my: 2 }} />
        
        <FormControlLabel
          control={<Switch defaultChecked />}
          label="Enable notifications"
        />
        <br />
        <FormControlLabel
          control={<Switch defaultChecked />}
          label="Show quality metrics"
        />
        <br />
        <FormControlLabel
          control={<Switch />}
          label="Enable dark mode"
        />

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" gutterBottom>
          Account Information
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Email: {user?.signInDetails?.loginId}
        </Typography>
        
        <Box sx={{ mt: 3 }}>
          <Button variant="outlined" sx={{ mr: 2 }}>
            Change Password
          </Button>
          <Button variant="outlined" color="error">
            Delete Account
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}

