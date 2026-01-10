'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
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
  Email,
  Lock,
  Person,
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

export const RegisterForm = () => {
  const router = useRouter();
  const { register, isLoading, error, clearError } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const passwordStrength = calculatePasswordStrength(password);
  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;

  const validateEmail = (emailValue: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(emailValue);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!fullName.trim()) {
      setLocalError('Please enter your full name.');
      return;
    }

    if (!email) {
      setLocalError('Please enter your email address.');
      return;
    }

    if (!validateEmail(email)) {
      setLocalError('Please enter a valid email address.');
      return;
    }

    if (!password) {
      setLocalError('Please enter a password.');
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
      // Generate username from email (before the @)
      const username = email.split('@')[0];
      await register({ username, email, password, full_name: fullName });
      router.push('/dashboard');
    } catch {
      // Error handled by AuthContext
    }
  };

  const displayError = localError || error;

  return (
    <Box sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      py: 4
    }}>
      <Paper sx={{
        p: 4,
        width: '100%',
        maxWidth: 450,
        boxShadow: 3
      }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Create Your Account
        </Typography>

        <Typography variant="subtitle1" gutterBottom align="center" sx={{ mb: 3, color: 'text.secondary' }}>
          Join DataGod to access powerful public records data
        </Typography>

        {displayError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => { setLocalError(null); clearError(); }}>
            {displayError}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            label="Full Name"
            type="text"
            fullWidth
            margin="normal"
            variant="outlined"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoFocus
            disabled={isLoading}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Person color="action" />
                </InputAdornment>
              ),
            }}
            aria-label="Full name"
          />

          <TextField
            label="Email"
            type="email"
            fullWidth
            margin="normal"
            variant="outlined"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
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

          <TextField
            label="Password"
            type={showPassword ? 'text' : 'password'}
            fullWidth
            margin="normal"
            variant="outlined"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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
            aria-label="Password"
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
            label="Confirm Password"
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
            aria-label="Confirm password"
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
                Creating Account...
              </>
            ) : (
              'Create Account'
            )}
          </Button>

          <Typography variant="caption" color="text.secondary" align="center" display="block" sx={{ mb: 2 }}>
            By creating an account, you agree to our{' '}
            <Link href="/terms" passHref legacyBehavior>
              <MuiLink sx={{ cursor: 'pointer' }}>Terms of Service</MuiLink>
            </Link>
            {' '}and{' '}
            <Link href="/privacy" passHref legacyBehavior>
              <MuiLink sx={{ cursor: 'pointer' }}>Privacy Policy</MuiLink>
            </Link>
          </Typography>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2">
              Already have an account?{' '}
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
