'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
    Box,
    Container,
    Typography,
    Paper,
    Button,
    CircularProgress,
    Alert,
} from '@mui/material';
import { CheckCircleOutline, Dashboard, Settings } from '@mui/icons-material';
import { apiService } from '../../../services/api';

export default function CheckoutSuccessPage() {
    const searchParams = useSearchParams();
    const sessionId = searchParams.get('session_id');
    const [loading, setLoading] = useState(true);
    const [subscription, setSubscription] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await apiService.getSubscriptionStatus();
                setSubscription(res.data);
            } catch {
                // Still show success even if status fetch fails
                setSubscription({ tier: 'active', status: 'active' });
            } finally {
                setLoading(false);
            }
        };

        // Allow Stripe webhook a moment to process
        const timer = setTimeout(fetchStatus, 1500);
        return () => clearTimeout(timer);
    }, [sessionId]);

    if (loading) {
        return (
            <Container maxWidth="sm" sx={{ py: 8, textAlign: 'center' }}>
                <CircularProgress size={48} sx={{ mb: 3 }} />
                <Typography variant="h6" color="text.secondary">
                    Confirming your subscription...
                </Typography>
            </Container>
        );
    }

    return (
        <Container maxWidth="sm" sx={{ py: 8 }}>
            <Paper sx={{ p: 4, textAlign: 'center' }}>
                <CheckCircleOutline
                    sx={{ fontSize: 72, color: 'success.main', mb: 2 }}
                />

                <Typography variant="h4" gutterBottom fontWeight="bold">
                    Subscription Confirmed!
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                    Welcome to DataGod{' '}
                    <strong style={{ textTransform: 'capitalize' }}>
                        {subscription?.tier || 'Premium'}
                    </strong>
                    . Your account has been upgraded and all features are now unlocked.
                </Typography>

                {error && (
                    <Alert severity="warning" sx={{ mb: 3, textAlign: 'left' }}>
                        {error}
                    </Alert>
                )}

                <Alert severity="success" sx={{ mb: 3, textAlign: 'left' }}>
                    Your subscription is now <strong>active</strong>. You can manage it
                    anytime from Settings.
                </Alert>

                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 3 }}>
                    <Button
                        variant="contained"
                        size="large"
                        startIcon={<Dashboard />}
                        href="/dashboard"
                    >
                        Go to Dashboard
                    </Button>
                    <Button
                        variant="outlined"
                        size="large"
                        startIcon={<Settings />}
                        href="/settings"
                    >
                        Manage Subscription
                    </Button>
                </Box>
            </Paper>
        </Container>
    );
}
