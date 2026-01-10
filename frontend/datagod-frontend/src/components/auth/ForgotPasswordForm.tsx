'use client';

import { useState } from 'react';
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
} from '@mui/material';
import { Email, CheckCircle, ArrowBack } from '@mui/icons-material';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';

export const ForgotPasswordForm = () => {
  const { resetPassword, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [success, setSuccess] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const validateEmail = (emailValue: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(emailValue);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email) {
      setLocalError('Please enter your email address.');
      return;
    }

    if (!validateEmail(email)) {
      setLocalError('Please enter a valid email address.');
      return;
    }

    try {
      await resetPassword(email);
      setSuccess(true);
    } catch {
      // Error handled by AuthContext
    }
  };

  const displayError = localError || error;

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
            Check Your Email
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            We&apos;ve sent a password reset link to <strong>{email}</strong>. Please check your inbox and follow the instructions to reset your password.
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Didn&apos;t receive the email? Check your spam folder or{' '}
            <MuiLink
              component="button"
              type="button"
              onClick={() => setSuccess(false)}
              sx={{ cursor: 'pointer', fontWeight: 'bold' }}
            >
              try again
            </MuiLink>
          </Typography>

          <Link href="/login" passHref legacyBehavior>
            <Button
              variant="contained"
              color="primary"
              fullWidth
              size="large"
              component="a"
              startIcon={<ArrowBack />}
            >
              Back to Login
            </Button>
          </Link>
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
          Forgot Password
        </Typography>

        <Typography variant="subtitle1" gutterBottom align="center" sx={{ mb: 3, color: 'text.secondary' }}>
          Enter your email to receive a password reset link
        </Typography>

        {displayError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => { setLocalError(null); clearError(); }}>
            {displayError}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            label="Email"
            type="email"
            fullWidth
            margin="normal"
            variant="outlined"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
            disabled={isLoading}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Email color="action" />
                </InputAdornment>
              ),
            }}
            aria-label="Email address"
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
                Sending...
              </>
            ) : (
              'Send Reset Link'
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
