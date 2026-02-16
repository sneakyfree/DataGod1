'use client';

import { useState, useEffect } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  IconButton,
} from '@mui/material';
import {
  Person,
  Notifications,
  Security,
  CreditCard,
  Visibility,
  VisibilityOff,
  Check,
} from '@mui/icons-material';
import { ProtectedRoute, useAuth } from '../../context/AuthContext';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../services/api';

function PasswordChangeModal({
  open,
  onClose
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const resetForm = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError(null);
    setSuccess(false);
  };

  const changeMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      apiService.changePassword(data),
    onSuccess: () => {
      setSuccess(true);
      setTimeout(() => {
        resetForm();
        onClose();
      }, 2000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to change password');
    }
  });

  const handleSubmit = () => {
    setError(null);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('All fields are required');
      return;
    }

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (currentPassword === newPassword) {
      setError('New password must be different from current password');
      return;
    }

    changeMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword
    });
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Change Password</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2, mt: 1 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2, mt: 1 }} icon={<Check />}>
            Password changed successfully!
          </Alert>
        )}

        <TextField
          fullWidth
          label="Current Password"
          type={showCurrentPassword ? 'text' : 'password'}
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          disabled={changeMutation.isPending || success}
          sx={{ mt: 2, mb: 2 }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  edge="end"
                >
                  {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        <TextField
          fullWidth
          label="New Password"
          type={showNewPassword ? 'text' : 'password'}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          disabled={changeMutation.isPending || success}
          helperText="At least 8 characters"
          sx={{ mb: 2 }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  edge="end"
                >
                  {showNewPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        <TextField
          fullWidth
          label="Confirm New Password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          disabled={changeMutation.isPending || success}
          error={confirmPassword.length > 0 && confirmPassword !== newPassword}
          helperText={
            confirmPassword.length > 0 && confirmPassword !== newPassword
              ? 'Passwords do not match'
              : ''
          }
        />
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={handleClose} disabled={changeMutation.isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={changeMutation.isPending || success}
          startIcon={changeMutation.isPending ? <CircularProgress size={20} /> : null}
        >
          {changeMutation.isPending ? 'Changing...' : 'Change Password'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function SettingsContent() {
  const { user, updateProfile, isLoading, error, clearError } = useAuth();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
  });
  const [success, setSuccess] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [notificationsSaving, setNotificationsSaving] = useState(false);

  // Fetch notification settings
  const { data: notificationSettings, isLoading: loadingNotifications } = useQuery({
    queryKey: ['notification-settings'],
    queryFn: async () => {
      const response = await apiService.getNotificationSettings();
      return response.data;
    }
  });

  const [notifications, setNotifications] = useState({
    email_updates: true,
    security_alerts: true,
    marketing: false,
    weekly_digest: true,
  });

  // Update local state when settings load
  useEffect(() => {
    if (notificationSettings) {
      setNotifications({
        email_updates: notificationSettings.email_updates ?? true,
        security_alerts: notificationSettings.security_alerts ?? true,
        marketing: notificationSettings.marketing ?? false,
        weekly_digest: notificationSettings.weekly_digest ?? true,
      });
    }
  }, [notificationSettings]);

  // Update form when user changes
  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || '',
        email: user.email || '',
      });
    }
  }, [user]);

  // Notification update mutation
  const notificationMutation = useMutation({
    mutationFn: (data: typeof notifications) =>
      apiService.updateNotificationSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-settings'] });
      setNotificationsSaving(false);
    },
    onError: () => {
      setNotificationsSaving(false);
    }
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleNotificationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newNotifications = {
      ...notifications,
      [e.target.name]: e.target.checked,
    };
    setNotifications(newNotifications);
    setNotificationsSaving(true);

    // Debounced save
    notificationMutation.mutate(newNotifications);
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
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Notifications color="primary" />
            <Typography variant="h6">Notification Preferences</Typography>
          </Box>
          {notificationsSaving && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CircularProgress size={16} />
              <Typography variant="caption" color="text.secondary">Saving...</Typography>
            </Box>
          )}
        </Box>

        {loadingNotifications ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
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
        )}
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
                Keep your account secure with a strong password
              </Typography>
            </Box>
            <Button variant="outlined" onClick={() => setPasswordModalOpen(true)}>
              Change Password
            </Button>
          </Box>

          <Divider />

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="subtitle1">Two-Factor Authentication</Typography>
              <Typography variant="body2" color="text.secondary">
                Add an extra layer of security to your account
              </Typography>
            </Box>
            <Button variant="outlined" disabled>
              Coming Soon
            </Button>
          </Box>

          <Divider />

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="subtitle1">Active Sessions</Typography>
              <Typography variant="body2" color="text.secondary">
                Manage devices that are logged into your account
              </Typography>
            </Box>
            <Button variant="outlined" disabled>
              Coming Soon
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* Subscription Settings */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <CreditCard color="primary" />
          <Typography variant="h6">Subscription</Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="subtitle1">
              Current Plan: <strong style={{ textTransform: 'capitalize' }}>{user?.subscription_tier || 'Free'}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {user?.subscription_tier && user.subscription_tier !== 'free'
                ? 'Your subscription renews monthly'
                : 'Upgrade to access more features'}
            </Typography>
          </Box>
          <Button variant="contained" color="primary" href="/pricing">
            {user?.subscription_tier && user.subscription_tier !== 'free'
              ? 'Change Plan'
              : 'Upgrade Plan'}
          </Button>
        </Box>

        {user?.subscription_tier && user.subscription_tier !== 'free' && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                onClick={async () => {
                  try {
                    const res = await apiService.createPortalSession();
                    if (res.data?.portal_url) {
                      window.location.href = res.data.portal_url;
                    }
                  } catch {
                    setLocalError('Could not open billing portal');
                  }
                }}
              >
                Manage Billing
              </Button>
              <Button
                variant="outlined"
                color="error"
                onClick={async () => {
                  if (!window.confirm('Are you sure you want to cancel your subscription? You will lose access to premium features.')) return;
                  try {
                    await apiService.cancelSubscription();
                    window.location.reload();
                  } catch {
                    setLocalError('Could not cancel subscription');
                  }
                }}
              >
                Cancel Subscription
              </Button>
            </Box>
          </>
        )}
      </Paper>

      {/* Password Change Modal */}
      <PasswordChangeModal
        open={passwordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
      />
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
