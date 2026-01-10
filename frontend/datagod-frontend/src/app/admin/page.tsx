'use client';

import { Box, Typography, Grid, Card, CardContent, CardActionArea, Chip } from '@mui/material';
import { useRouter } from 'next/navigation';
import MapIcon from '@mui/icons-material/Map';
import AssessmentIcon from '@mui/icons-material/Assessment';
import PeopleIcon from '@mui/icons-material/People';
import SettingsIcon from '@mui/icons-material/Settings';
import StorageIcon from '@mui/icons-material/Storage';
import SecurityIcon from '@mui/icons-material/Security';
import { MainLayout } from '../../components/layout/MainLayout';

interface AdminCard {
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  badge?: string;
  badgeColor?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
}

const adminCards: AdminCard[] = [
  {
    title: 'Coverage Dashboard',
    description: 'Monitor and manage data coverage across all US jurisdictions',
    icon: <MapIcon sx={{ fontSize: 48 }} />,
    path: '/admin/coverage',
    badge: '3,240 counties',
    badgeColor: 'primary',
  },
  {
    title: 'Data Quality',
    description: 'Review data quality metrics and validation reports',
    icon: <AssessmentIcon sx={{ fontSize: 48 }} />,
    path: '/admin/quality',
  },
  {
    title: 'User Management',
    description: 'Manage user accounts, permissions, and subscriptions',
    icon: <PeopleIcon sx={{ fontSize: 48 }} />,
    path: '/admin/users',
  },
  {
    title: 'Scraper Status',
    description: 'Monitor active scrapers and data ingestion pipelines',
    icon: <StorageIcon sx={{ fontSize: 48 }} />,
    path: '/admin/scrapers',
    badge: 'Active',
    badgeColor: 'success',
  },
  {
    title: 'System Settings',
    description: 'Configure system-wide settings and parameters',
    icon: <SettingsIcon sx={{ fontSize: 48 }} />,
    path: '/admin/settings',
  },
  {
    title: 'Security & Audit',
    description: 'View security logs and audit trails',
    icon: <SecurityIcon sx={{ fontSize: 48 }} />,
    path: '/admin/security',
  },
];

export default function AdminDashboard() {
  const router = useRouter();

  return (
    <MainLayout>
      <Box sx={{ p: 3 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Admin Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage DataGod platform settings, users, and data coverage
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {adminCards.map((card) => (
            <Grid item xs={12} sm={6} md={4} key={card.title}>
              <Card
                sx={{
                  height: '100%',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
              >
                <CardActionArea
                  onClick={() => router.push(card.path)}
                  sx={{ height: '100%', p: 2 }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box sx={{ color: 'primary.main' }}>
                        {card.icon}
                      </Box>
                      {card.badge && (
                        <Chip
                          label={card.badge}
                          size="small"
                          color={card.badgeColor || 'default'}
                        />
                      )}
                    </Box>
                    <Typography variant="h6" component="h2" gutterBottom>
                      {card.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {card.description}
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Quick Stats */}
        <Box sx={{ mt: 4 }}>
          <Typography variant="h6" gutterBottom>
            Platform Overview
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    3,240
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Jurisdictions
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    56
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    States/Territories
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="success.main">
                    15
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Data Categories
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="warning.main">
                    0.12%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Coverage Rate
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      </Box>
    </MainLayout>
  );
}
