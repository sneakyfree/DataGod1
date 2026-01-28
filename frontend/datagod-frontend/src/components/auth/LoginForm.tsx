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
  Checkbox,
  FormControlLabel,
  Divider,
} from '@mui/material';
import { Visibility, VisibilityOff, Email, Lock, AdminPanelSettings, Person, SupervisorAccount, Badge } from '@mui/icons-material';
import Link from 'next/link';
import { useAuth } from '../../context/AuthContext';
import OAuthButtons from './OAuthButtons';

// Quick login accounts for development
const QUICK_LOGIN_ACCOUNTS = [
  { label: 'Super Admin', email: 'superadmin@datagod.local', password: 'superadmin123', icon: <AdminPanelSettings />, color: '#d32f2f' },
  { label: 'Admin', email: 'admin@datagod.local', password: 'admin123', icon: <SupervisorAccount />, color: '#1976d2' },
  { label: 'User', email: 'user@datagod.local', password: 'user123', icon: <Person />, color: '#388e3c' },
  { label: 'Sales Rep', email: 'salesrep@datagod.local', password: 'sales123', icon: <Badge />, color: '#f57c00' },
];

export const LoginForm = () => {
  const router = useRouter();
  const { login, isLoading, error, clearError } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
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

    if (!password) {
      setLocalError('Please enter your password.');
      return;
    }

    try {
      await login({ email, password });
      router.push('/dashboard');
    } catch {
      // Error handled by AuthContext
    }
  };

  const handleQuickLogin = async (account: typeof QUICK_LOGIN_ACCOUNTS[0]) => {
    setLocalError(null);
    clearError();
    setEmail(account.email);
    setPassword(account.password);

    try {
      await login({ email: account.email, password: account.password });
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
      backgroundColor: '#f5f5f5'
    }}>
      <Paper sx={{
        p: 4,
        width: '100%',
        maxWidth: 450,
        boxShadow: 3
      }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Welcome to DataGod
        </Typography>

        <Typography variant="subtitle1" gutterBottom align="center" sx={{ mb: 3, color: 'text.secondary' }}>
          Sign in to access your account
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

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1, mb: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  color="primary"
                  disabled={isLoading}
                />
              }
              label="Remember me"
            />
            <Link href="/forgot-password" passHref legacyBehavior>
              <MuiLink variant="body2" sx={{ cursor: 'pointer' }}>
                Forgot password?
              </MuiLink>
            </Link>
          </Box>

          <Button
            type="submit"
            variant="contained"
            color="primary"
            fullWidth
            size="large"
            disabled={isLoading}
            sx={{ mb: 2, py: 1.5 }}
          >
            {isLoading ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} color="inherit" />
                Signing In...
              </>
            ) : (
              'Sign In'
            )}
          </Button>

          <Box sx={{ textAlign: 'center', mb: 2 }}>
            <Typography variant="body2">
              Don&apos;t have an account?{' '}
              <Link href="/register" passHref legacyBehavior>
                <MuiLink sx={{ fontWeight: 'bold', cursor: 'pointer' }}>
                  Sign Up
                </MuiLink>
              </Link>
            </Typography>
          </Box>
        </form>

        {/* OAuth SSO Options */}
        <OAuthButtons mode="login" />

        {/* Quick Login Section */}
        <Divider sx={{ my: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Quick Login (Dev Only)
          </Typography>
        </Divider>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
          {QUICK_LOGIN_ACCOUNTS.map((account) => (
            <Button
              key={account.email}
              variant="outlined"
              size="small"
              startIcon={account.icon}
              onClick={() => handleQuickLogin(account)}
              disabled={isLoading}
              sx={{
                borderColor: account.color,
                color: account.color,
                '&:hover': {
                  borderColor: account.color,
                  backgroundColor: `${account.color}10`,
                },
                textTransform: 'none',
                fontSize: '0.75rem',
                py: 0.75,
              }}
            >
              {account.label}
            </Button>
          ))}
        </Box>
      </Paper>
    </Box>
  );
};
