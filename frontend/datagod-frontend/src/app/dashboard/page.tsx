'use client';

import { Box, Typography, Grid, Paper, Skeleton } from '@mui/material';
import { ProtectedRoute } from '../../context/AuthContext';
import { DashboardStats } from '../../components/DashboardStats';
import { RecentRecords } from '../../components/RecentRecords';
import { useAuth } from '../../context/AuthContext';

function DashboardContent() {
  const { user } = useAuth();

  return (
    <Box sx={{ flexGrow: 1, p: { xs: 2, sm: 3 } }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome back{user?.full_name ? `, ${user.full_name}` : ''}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here&apos;s an overview of your DataGod dashboard
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12}>
          <DashboardStats />
        </Grid>

        {/* Main Content */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Records
            </Typography>
            <RecentRecords limit={10} />
          </Paper>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <QuickActionItem
                title="Search Records"
                description="Search across all jurisdictions"
                href="/search"
              />
              <QuickActionItem
                title="View Records"
                description="Browse all available records"
                href="/records"
              />
              <QuickActionItem
                title="Jurisdictions"
                description="Explore coverage by region"
                href="/jurisdictions"
              />
              <QuickActionItem
                title="Account Settings"
                description="Manage your profile and preferences"
                href="/settings"
              />
            </Box>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Subscription Status
            </Typography>
            <SubscriptionStatus />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

// Quick action item component
function QuickActionItem({ title, description, href }: { title: string; description: string; href: string }) {
  return (
    <Box
      component="a"
      href={href}
      sx={{
        p: 1.5,
        borderRadius: 1,
        textDecoration: 'none',
        color: 'inherit',
        backgroundColor: 'grey.50',
        transition: 'all 0.2s ease',
        display: 'block',
        '&:hover': {
          backgroundColor: 'primary.light',
          color: 'primary.contrastText',
        },
      }}
    >
      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ '&:hover': { color: 'inherit' } }}>
        {description}
      </Typography>
    </Box>
  );
}

// Subscription status component
function SubscriptionStatus() {
  const { user } = useAuth();

  // Map subscription tier to display info
  const getTierInfo = (tier: string | undefined) => {
    switch (tier?.toLowerCase()) {
      case 'enterprise':
        return { label: 'Enterprise', color: '#6b21a8', bgColor: '#f3e8ff' };
      case 'pro':
        return { label: 'Pro', color: '#0369a1', bgColor: '#e0f2fe' };
      case 'basic':
        return { label: 'Basic', color: '#166534', bgColor: '#dcfce7' };
      default:
        return { label: 'Free', color: '#525252', bgColor: '#f5f5f5' };
    }
  };

  const tierInfo = getTierInfo(user?.subscription_tier);

  return (
    <Box>
      <Box sx={{
        display: 'inline-block',
        px: 2,
        py: 0.5,
        borderRadius: 2,
        backgroundColor: tierInfo.bgColor,
        color: tierInfo.color,
        fontWeight: 600,
        fontSize: '0.875rem',
        mb: 2
      }}>
        {tierInfo.label} Plan
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {tierInfo.label === 'Free'
          ? 'Upgrade to unlock more features and higher limits.'
          : 'Thank you for being a valued subscriber!'}
      </Typography>
      {tierInfo.label === 'Free' && (
        <Box
          component="a"
          href="/pricing"
          sx={{
            display: 'inline-block',
            px: 2,
            py: 1,
            borderRadius: 1,
            backgroundColor: 'primary.main',
            color: 'white',
            textDecoration: 'none',
            fontSize: '0.875rem',
            fontWeight: 500,
            transition: 'all 0.2s ease',
            '&:hover': {
              backgroundColor: 'primary.dark',
            },
          }}
        >
          Upgrade Now
        </Box>
      )}
    </Box>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
