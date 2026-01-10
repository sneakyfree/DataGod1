'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Link as MuiLink,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
  LinearProgress,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Lock,
  CheckCircle,
  Cancel,
} from '@mui/icons-material';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';

// Password strength calculator
const calculatePasswordStrength = (password: string): { score: number; label: string; color: string } => {
  let score = 0;

  if (password.length >= 8) score += 25;
  if (password.length >= 12) score += 15;
  if (/[a-z]/.test(password)) score += 15;
  if (/[A-Z]/.test(password)) score += 15;
  if (/[0-9]/.test(password)) score += 15;
  if (/[^a-zA-Z0-9]/.test(password)) score += 15;

  if (score < 30) return { score, label: 'Weak', color: '#f44336' };
  if (score < 60) return { score, label: 'Fair', color: '#ff9800' };
  if (score < 80) return { score, label: 'Good', color: '#2196f3' };
  return { score, label: 'Strong', color: '#4caf50' };
};

export const ResetPasswordForm = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const { confirmResetPassword, isLoading, error, clearError } = useAuth();

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [success, setSuccess] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const passwordStrength = calculatePasswordStrength(password);
  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!token) {
      setLocalError('Invalid or missing reset token. Please request a new password reset.');
      return;
    }

    if (!password) {
      setLocalError('Please enter a new password.');
      return;
    }

    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters long.');
      return;
    }

    if (passwordStrength.score < 30) {
      setLocalError('Please choose a stronger password.');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    try {
      await confirmResetPassword(token, password);
      setSuccess(true);
    } catch {
      // Error handled by AuthContext
    }
  };

  const displayError = localError || error;

  // Invalid or missing token state
  if (!token) {
    return (
      <Box sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f5f5f5'
      }}>
        <Paper sx={{
          p: 4,
          width: '100%',
          maxWidth: 450,
          boxShadow: 3,
          textAlign: 'center'
        }}>
          <Box sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            backgroundColor: '#ffebee',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px'
          }}>
            <Cancel sx={{ fontSize: 48, color: '#f44336' }} />
          </Box>

          <Typography variant="h4" component="h1" gutterBottom>
            Invalid Link
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            This password reset link is invalid or has expired. Please request a new password reset.
          </Typography>

          <Link href="/forgot-password" passHref legacyBehavior>
            <Button
              variant="contained"
              color="primary"
              fullWidth
              size="large"
              component="a"
            >
              Request New Reset Link
            </Button>
          </Link>
        </Paper>
      </Box>
    );
  }

  // Success state
  if (success) {
    return (
      <Box sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f5f5f5'
      }}>
        <Paper sx={{
          p: 4,
          width: '100%',
          maxWidth: 450,
          boxShadow: 3,
          textAlign: 'center'
        }}>
          <Box sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            backgroundColor: '#e8f5e9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px'
          }}>
            <CheckCircle sx={{ fontSize: 48, color: '#4caf50' }} />
          </Box>

          <Typography variant="h4" component="h1" gutterBottom>
            Password Reset Complete
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Your password has been successfully reset. You can now sign in with your new password.
          </Typography>

          <Button
            variant="contained"
            color="primary"
            fullWidth
            size="large"
            onClick={() => router.push('/login')}
          >
            Sign In
          </Button>
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5'
    }}>
      <Paper sx={{
        p: 4,
        width: '100%',
        maxWidth: 450,
        boxShadow: 3
      }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Reset Your Password
        </Typography>

        <Typography variant="subtitle1" gutterBottom align="center" sx={{ mb: 3, color: 'text.secondary' }}>
          Enter your new password below
        </Typography>

        {displayError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => { setLocalError(null); clearError(); }}>
            {displayError}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            label="New Password"
            type={showPassword ? 'text' : 'password'}
            fullWidth
            margin="normal"
            variant="outlined"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoFocus
            disabled={isLoading}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Lock color="action" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword(!showPassword)}
                    edge="end"
                    disabled={isLoading}
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
            aria-label="New password"
          />

          {password && (
            <Box sx={{ mt: 1, mb: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Password strength
                </Typography>
                <Typography variant="caption" sx={{ color: passwordStrength.color, fontWeight: 'bold' }}>
                  {passwordStrength.label}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={passwordStrength.score}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  backgroundColor: '#e0e0e0',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: passwordStrength.color,
                    borderRadius: 3,
                  },
                }}
              />
            </Box>
          )}

          <TextField
            label="Confirm New Password"
            type={showConfirmPassword ? 'text' : 'password'}
            fullWidth
            margin="normal"
            variant="outlined"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            disabled={isLoading}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Lock color="action" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  {confirmPassword && (
                    passwordsMatch ? (
                      <CheckCircle color="success" sx={{ mr: 1 }} />
                    ) : (
                      <Cancel color="error" sx={{ mr: 1 }} />
                    )
                  )}
                  <IconButton
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    edge="end"
                    disabled={isLoading}
                  >
                    {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
            error={confirmPassword.length > 0 && !passwordsMatch}
            helperText={confirmPassword.length > 0 && !passwordsMatch ? 'Passwords do not match' : ''}
            aria-label="Confirm new password"
          />

          <Button
            type="submit"
            variant="contained"
            color="primary"
            fullWidth
            size="large"
            disabled={isLoading}
            sx={{ mt: 2, mb: 2, py: 1.5 }}
          >
            {isLoading ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} color="inherit" />
                Resetting Password...
              </>
            ) : (
              'Reset Password'
            )}
          </Button>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2">
              Remember your password?{' '}
              <Link href="/login" passHref legacyBehavior>
                <MuiLink sx={{ fontWeight: 'bold', cursor: 'pointer' }}>
                  Sign In
                </MuiLink>
              </Link>
            </Typography>
          </Box>
        </form>
      </Paper>
    </Box>
  );
};
