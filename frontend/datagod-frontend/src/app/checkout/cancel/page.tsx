'use client';

import {
    Box,
    Container,
    Typography,
    Paper,
    Button,
} from '@mui/material';
import { Cancel, ArrowBack } from '@mui/icons-material';

export default function CheckoutCancelPage() {
    return (
        <Container maxWidth="sm" sx={{ py: 8 }}>
            <Paper sx={{ p: 4, textAlign: 'center' }}>
                <Cancel sx={{ fontSize: 72, color: 'warning.main', mb: 2 }} />

                <Typography variant="h4" gutterBottom fontWeight="bold">
                    Payment Cancelled
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                    Your payment was not processed. No charges have been made to your
                    account. You can try again whenever you are ready.
                </Typography>

                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 3 }}>
                    <Button
                        variant="contained"
                        size="large"
                        href="/pricing"
                    >
                        Back to Pricing
                    </Button>
                    <Button
                        variant="outlined"
                        size="large"
                        startIcon={<ArrowBack />}
                        href="/dashboard"
                    >
                        Dashboard
                    </Button>
                </Box>
            </Paper>
        </Container>
    );
}
