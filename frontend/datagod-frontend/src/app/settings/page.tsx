'use client';

import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Grid,
  Container,
  Alert,
  CircularProgress,
  Divider,
  Avatar,
  Switch,
  FormControlLabel,
  FormGroup,
} from '@mui/material';
import { Person, Notifications, Security, CreditCard } from '@mui/icons-material';
import { ProtectedRoute, useAuth } from '../../context/AuthContext';

function SettingsContent() {
  const { user, updateProfile, isLoading, error, clearError } = useAuth();

  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
  });
  const [notifications, setNotifications] = useState({
    email_updates: true,
    security_alerts: true,
    marketing: false,
    weekly_digest: true,
  });
  const [success, setSuccess] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleNotificationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNotifications(prev => ({
      ...prev,
      [e.target.name]: e.target.checked,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();
    setSuccess(false);

    try {
      await updateProfile(formData);
      setSuccess(true);
    } catch {
      setLocalError('Failed to update profile. Please try again.');
    }
  };

  const displayError = localError || error;

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Manage your account settings and preferences
      </Typography>

      {displayError && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => { setLocalError(null); clearError(); }}>
          {displayError}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(false)}>
          Settings updated successfully!
        </Alert>
      )}

      {/* Profile Settings */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Person color="primary" />
          <Typography variant="h6">Profile Information</Typography>
        </Box>

        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
              <Avatar
                sx={{ width: 80, height: 80, bgcolor: 'primary.main', fontSize: '2rem' }}
              >
                {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
              </Avatar>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Full Name"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                disabled={isLoading}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                disabled={isLoading}
              />
            </Grid>

            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={isLoading}
                startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </Button>
            </Grid>
          </Grid>
        </form>
      </Paper>

      {/* Notification Settings */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Notifications color="primary" />
          <Typography variant="h6">Notification Preferences</Typography>
        </Box>

        <FormGroup>
          <FormControlLabel
            control={
              <Switch
                checked={notifications.email_updates}
                onChange={handleNotificationChange}
                name="email_updates"
              />
            }
            label="Email updates about new records and features"
          />
          <FormControlLabel
            control={
              <Switch
                checked={notifications.security_alerts}
                onChange={handleNotificationChange}
                name="security_alerts"
              />
            }
            label="Security alerts and account notifications"
          />
          <FormControlLabel
            control={
              <Switch
                checked={notifications.weekly_digest}
                onChange={handleNotificationChange}
                name="weekly_digest"
              />
            }
            label="Weekly digest of activity in your searches"
          />
          <FormControlLabel
            control={
              <Switch
                checked={notifications.marketing}
                onChange={handleNotificationChange}
                name="marketing"
              />
            }
            label="Marketing and promotional emails"
          />
        </FormGroup>
      </Paper>

      {/* Security Settings */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Security color="primary" />
          <Typography variant="h6">Security</Typography>
        </Box>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="subtitle1">Password</Typography>
              <Typography variant="body2" color="text.secondary">
                Last changed: Never
              </Typography>
            </Box>
            <Button variant="outlined">Change Password</Button>
          </Box>

          <Divider />

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="subtitle1">Two-Factor Authentication</Typography>
              <Typography variant="body2" color="text.secondary">
                Add an extra layer of security to your account
              </Typography>
            </Box>
            <Button variant="outlined">Enable</Button>
          </Box>

          <Divider />

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="subtitle1">Active Sessions</Typography>
              <Typography variant="body2" color="text.secondary">
                Manage devices that are logged into your account
              </Typography>
            </Box>
            <Button variant="outlined">View Sessions</Button>
          </Box>
        </Box>
      </Paper>

      {/* Subscription Settings */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <CreditCard color="primary" />
          <Typography variant="h6">Subscription</Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="subtitle1">
              Current Plan: <strong>{user?.subscription_tier || 'Free'}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {user?.subscription_tier && user.subscription_tier !== 'free'
                ? 'Your subscription renews monthly'
                : 'Upgrade to access more features'}
            </Typography>
          </Box>
          <Button variant="contained" color="primary" href="/pricing">
            {user?.subscription_tier && user.subscription_tier !== 'free'
              ? 'Manage Subscription'
              : 'Upgrade Plan'}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <SettingsContent />
    </ProtectedRoute>
  );
}
