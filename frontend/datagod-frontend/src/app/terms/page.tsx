'use client';

import { Box, Typography, Paper, Container } from '@mui/material';

export default function TermsPage() {
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper sx={{ p: { xs: 3, md: 5 } }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Terms of Service
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Last updated: December 30, 2025
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          1. Acceptance of Terms
        </Typography>
        <Typography variant="body1" paragraph>
          By accessing or using DataGod (&quot;the Service&quot;), you agree to be bound by
          these Terms of Service (&quot;Terms&quot;). If you do not agree to these Terms,
          you may not access or use the Service.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          2. Description of Service
        </Typography>
        <Typography variant="body1" paragraph>
          DataGod provides access to aggregated public records data from various
          government jurisdictions across the United States. The Service includes
          search functionality, data export features, and API access depending on
          your subscription tier.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          3. User Accounts
        </Typography>
        <Typography variant="body1" component="div">
          <ul>
            <li>You must provide accurate and complete registration information</li>
            <li>You are responsible for maintaining the security of your account</li>
            <li>You must notify us immediately of any unauthorized use</li>
            <li>You may not share your account credentials with others</li>
            <li>One account per person/organization is permitted</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          4. Acceptable Use
        </Typography>
        <Typography variant="body1" paragraph>
          You agree NOT to use the Service to:
        </Typography>
        <Typography variant="body1" component="div">
          <ul>
            <li>Violate any applicable laws or regulations</li>
            <li>Infringe on the rights of others</li>
            <li>Harass, stalk, or harm any individual</li>
            <li>Scrape or collect data beyond your subscription limits</li>
            <li>Attempt to gain unauthorized access to our systems</li>
            <li>Interfere with or disrupt the Service</li>
            <li>Resell or redistribute data without authorization</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          5. Data and Content
        </Typography>
        <Typography variant="body1" paragraph>
          The data provided through DataGod is sourced from public records.
          While we strive for accuracy, we do not guarantee the completeness,
          accuracy, or timeliness of any data. Users should independently verify
          information for critical decisions.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          6. Subscription and Payments
        </Typography>
        <Typography variant="body1" component="div">
          <ul>
            <li>Paid subscriptions are billed in advance on a monthly or annual basis</li>
            <li>You authorize us to charge your payment method automatically</li>
            <li>Subscription fees are non-refundable except as required by law</li>
            <li>We may change pricing with 30 days&apos; notice</li>
            <li>Failure to pay may result in service suspension</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          7. Intellectual Property
        </Typography>
        <Typography variant="body1" paragraph>
          The Service, including its design, features, and code, is owned by
          DataGod and protected by intellectual property laws. You may not copy,
          modify, or distribute any part of the Service without our written consent.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          8. Disclaimer of Warranties
        </Typography>
        <Typography variant="body1" paragraph>
          THE SERVICE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTIES OF ANY KIND,
          EXPRESS OR IMPLIED. WE DISCLAIM ALL WARRANTIES, INCLUDING MERCHANTABILITY,
          FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          9. Limitation of Liability
        </Typography>
        <Typography variant="body1" paragraph>
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, DATAGOD SHALL NOT BE LIABLE
          FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES
          ARISING OUT OF OR RELATING TO YOUR USE OF THE SERVICE.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          10. Termination
        </Typography>
        <Typography variant="body1" paragraph>
          We may suspend or terminate your account at any time for violation of
          these Terms or for any other reason at our sole discretion. Upon
          termination, your right to use the Service will cease immediately.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          11. Governing Law
        </Typography>
        <Typography variant="body1" paragraph>
          These Terms shall be governed by and construed in accordance with the
          laws of the State of California, without regard to its conflict of law
          provisions.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          12. Changes to Terms
        </Typography>
        <Typography variant="body1" paragraph>
          We reserve the right to modify these Terms at any time. We will notify
          you of any material changes by posting the new Terms on our website.
          Your continued use of the Service after such changes constitutes your
          acceptance of the new Terms.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          13. Contact Information
        </Typography>
        <Typography variant="body1" paragraph>
          For questions about these Terms, please contact us at:
        </Typography>
        <Typography variant="body1" component="div">
          <ul>
            <li>Email: legal@datagod.io</li>
            <li>Address: 123 Data Street, Suite 100, San Francisco, CA 94102</li>
          </ul>
        </Typography>
      </Paper>
    </Container>
  );
}
