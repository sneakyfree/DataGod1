'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Box, CircularProgress, Typography } from '@mui/material';
import { ProtectedRoute } from '../../context/AuthContext';

/**
 * Profile page - redirects to settings which contains full profile management.
 * The settings page at /settings already has profile editing (name, email, avatar),
 * notification preferences, password change, security, and subscription management.
 */
function ProfileRedirect() {
    const router = useRouter();

    useEffect(() => {
        router.replace('/settings');
    }, [router]);

    return (
        <Box
            sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '60vh',
                gap: 2,
            }}
        >
            <CircularProgress />
            <Typography color="text.secondary">Redirecting to settings...</Typography>
        </Box>
    );
}

export default function ProfilePage() {
    return (
        <ProtectedRoute>
            <ProfileRedirect />
        </ProtectedRoute>
    );
}
