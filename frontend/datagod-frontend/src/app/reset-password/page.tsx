'use client';

import { Suspense } from 'react';
import { Box, CircularProgress } from '@mui/material';
import { ResetPasswordForm } from '../../components/auth/ResetPasswordForm';

// Loading component for Suspense
function LoadingFallback() {
  return (
    <Box sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5'
    }}>
      <CircularProgress />
    </Box>
  );
}

// Wrap component that uses useSearchParams
function ResetPasswordContent() {
  return <ResetPasswordForm />;
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ResetPasswordContent />
    </Suspense>
  );
}
