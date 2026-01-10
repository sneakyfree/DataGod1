'use client';

import { Box, Typography, Paper, Container } from '@mui/material';

export default function PrivacyPage() {
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper sx={{ p: { xs: 3, md: 5 } }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Privacy Policy
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Last updated: December 30, 2025
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          1. Introduction
        </Typography>
        <Typography variant="body1" paragraph>
          DataGod (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) is committed to protecting your privacy.
          This Privacy Policy explains how we collect, use, disclose, and safeguard
          your information when you use our public records search platform.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          2. Information We Collect
        </Typography>
        <Typography variant="body1" component="div">
          <strong>Personal Information:</strong>
          <ul>
            <li>Name and email address when you create an account</li>
            <li>Payment information when you subscribe to paid plans</li>
            <li>Usage data including search queries and accessed records</li>
            <li>Device information and IP addresses</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          3. How We Use Your Information
        </Typography>
        <Typography variant="body1" component="div">
          We use collected information to:
          <ul>
            <li>Provide and maintain our services</li>
            <li>Process transactions and send related information</li>
            <li>Send promotional communications (with your consent)</li>
            <li>Respond to your comments, questions, and requests</li>
            <li>Monitor and analyze usage patterns to improve our services</li>
            <li>Detect, prevent, and address technical issues</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          4. Information Sharing
        </Typography>
        <Typography variant="body1" paragraph>
          We do not sell your personal information. We may share information with:
        </Typography>
        <Typography variant="body1" component="div">
          <ul>
            <li><strong>Service Providers:</strong> Third parties that help us operate our platform</li>
            <li><strong>Legal Requirements:</strong> When required by law or to protect our rights</li>
            <li><strong>Business Transfers:</strong> In connection with a merger or acquisition</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          5. Data Security
        </Typography>
        <Typography variant="body1" paragraph>
          We implement appropriate technical and organizational security measures to
          protect your personal information. However, no method of transmission over
          the Internet is 100% secure, and we cannot guarantee absolute security.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          6. Your Rights
        </Typography>
        <Typography variant="body1" component="div">
          Depending on your location, you may have rights to:
          <ul>
            <li>Access your personal information</li>
            <li>Correct inaccurate data</li>
            <li>Request deletion of your data</li>
            <li>Object to processing of your data</li>
            <li>Request data portability</li>
            <li>Withdraw consent</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          7. Cookies and Tracking
        </Typography>
        <Typography variant="body1" paragraph>
          We use cookies and similar tracking technologies to collect and track
          information about your activity on our platform. You can instruct your
          browser to refuse all cookies or indicate when a cookie is being sent.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          8. Children&apos;s Privacy
        </Typography>
        <Typography variant="body1" paragraph>
          Our services are not intended for individuals under 18 years of age.
          We do not knowingly collect personal information from children.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          9. Changes to This Policy
        </Typography>
        <Typography variant="body1" paragraph>
          We may update this Privacy Policy from time to time. We will notify you
          of any changes by posting the new policy on this page and updating the
          &quot;Last updated&quot; date.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          10. Contact Us
        </Typography>
        <Typography variant="body1" paragraph>
          If you have questions about this Privacy Policy, please contact us at:
        </Typography>
        <Typography variant="body1" component="div">
          <ul>
            <li>Email: privacy@datagod.io</li>
            <li>Address: 123 Data Street, Suite 100, San Francisco, CA 94102</li>
          </ul>
        </Typography>
      </Paper>
    </Container>
  );
}
