'use client';

import { useSearchParams } from 'next/navigation';
import CheckoutSuccessPage from '../../checkout/success/page';

// Backend generates success_url pointing to /subscription/success
// This route aliases to the same checkout success component
export default function SubscriptionSuccessPage() {
    return <CheckoutSuccessPage />;
}
