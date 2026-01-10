'use client';

import { Container } from '@mui/material';
import { PricingPage } from '../../components/subscription/PricingPage';

export default function PricingPageRoute() {
  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <PricingPage />
    </Container>
  );
}
