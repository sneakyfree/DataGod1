import { useState } from 'react';
import { Box, Typography, Paper, Button, Grid, Card, CardContent, CardActions, Divider, Chip, CircularProgress, Alert } from '@mui/material';
import { Check, Close } from '@mui/icons-material';
import { apiService } from '../../services/api';

const subscriptionTiers = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    billing: 'Forever',
    features: [
      'Access to basic records',
      'Limited search results',
      'Basic visualizations',
      'Community support',
      'Up to 100 records/month',
    ],
    excludedFeatures: [
      'Advanced search filters',
      'API access',
      'Export functionality',
      'Priority support',
      'Custom reports',
    ],
    buttonText: 'Get Started',
    buttonVariant: 'outlined' as const,
  },
  {
    id: 'basic',
    name: 'Basic',
    price: '$29',
    billing: 'per month',
    features: [
      'Access to all records',
      'Advanced search filters',
      'Export to CSV/Excel',
      'Email support',
      'Up to 1,000 records/month',
      'Basic API access',
    ],
    excludedFeatures: [
      'Priority support',
      'Custom reports',
      'Team collaboration',
      'Advanced analytics',
      'White-label reports',
    ],
    buttonText: 'Subscribe',
    buttonVariant: 'contained' as const,
    popular: true,
  },
  {
    id: 'pro',
    name: 'Professional',
    price: '$99',
    billing: 'per month',
    features: [
      'Unlimited records access',
      'Full API access',
      'Advanced analytics',
      'Priority support',
      'Custom reports',
      'Team collaboration (up to 5 users)',
      'Export to multiple formats',
      'Advanced visualizations',
    ],
    excludedFeatures: [
      'White-label reports',
      'Dedicated account manager',
      'Custom integrations',
      'Enterprise SLAs',
    ],
    buttonText: 'Subscribe',
    buttonVariant: 'contained' as const,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    billing: 'Contact us',
    features: [
      'All Pro features',
      'White-label reports',
      'Dedicated account manager',
      'Custom integrations',
      'Enterprise SLAs',
      'Unlimited team members',
      'Custom data pipelines',
      'Priority feature requests',
    ],
    excludedFeatures: [],
    buttonText: 'Contact Sales',
    buttonVariant: 'contained' as const,
  },
];

export const PricingPage = () => {
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubscribe = async (tierId: string) => {
    if (tierId === 'free') return;

    if (tierId === 'enterprise') {
      window.location.href = '/contact';
      return;
    }

    setSelectedTier(tierId);
    setLoading(true);
    setError(null);

    try {
      const res = await apiService.subscribe({ tier: tierId });
      const data = res.data;

      if (data.checkout_url) {
        // Stripe mode — redirect to Stripe Checkout
        window.location.href = data.checkout_url;
      } else if (data.status === 'active') {
        // Mock mode — subscription activated directly
        setSuccess(true);
        setLoading(false);
        setTimeout(() => {
          window.location.href = '/checkout/success?session_id=mock';
        }, 1500);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Subscription failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      <Typography
        variant="h3"
        component="h1"
        gutterBottom
        align="center"
        sx={{ fontSize: { xs: '1.75rem', sm: '2.5rem', md: '3rem' } }}
      >
        Choose Your Plan
      </Typography>

      <Typography
        variant="subtitle1"
        gutterBottom
        align="center"
        sx={{
          mb: { xs: 2, sm: 4 },
          fontSize: { xs: '0.875rem', sm: '1rem' }
        }}
      >
        Simple, transparent pricing that scales with your needs
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Subscription successful! You now have access to {selectedTier} features.
        </Alert>
      )}

      <Grid container spacing={{ xs: 2, sm: 3 }}>
        {subscriptionTiers.map((tier) => (
          <Grid item xs={12} sm={6} md={3} key={tier.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                border: tier.popular ? '2px solid' : '1px solid',
                borderColor: tier.popular ? 'primary.main' : 'divider',
                position: 'relative',
              }}
            >
              {tier.popular && (
                <Chip
                  label="Most Popular"
                  color="primary"
                  size="small"
                  sx={{
                    position: 'absolute',
                    top: -12,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 1,
                  }}
                />
              )}

              <CardContent sx={{ flexGrow: 1, p: { xs: 2, sm: 2 } }}>
                <Typography
                  variant="h5"
                  component="div"
                  gutterBottom
                  sx={{ fontSize: { xs: '1.25rem', sm: '1.5rem' } }}
                >
                  {tier.name}
                </Typography>

                <Box sx={{ mb: 2 }}>
                  <Typography
                    variant="h3"
                    component="span"
                    sx={{ fontSize: { xs: '1.75rem', sm: '2rem', md: '2.5rem' } }}
                  >
                    {tier.price}
                  </Typography>
                  <Typography variant="body2" component="span" sx={{ ml: 1 }}>
                    {tier.billing}
                  </Typography>
                </Box>

                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Features:
                </Typography>

                <Box sx={{ mb: 2 }}>
                  {tier.features.map((feature, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                      <Check color="success" sx={{ mr: 1, fontSize: 16 }} />
                      <Typography variant="body2">{feature}</Typography>
                    </Box>
                  ))}
                </Box>

                {tier.excludedFeatures.length > 0 && (
                  <>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Not included:
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      {tier.excludedFeatures.map((feature, index) => (
                        <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                          <Close color="disabled" sx={{ mr: 1, fontSize: 16 }} />
                          <Typography variant="body2" color="text.secondary">{feature}</Typography>
                        </Box>
                      ))}
                    </Box>
                  </>
                )}
              </CardContent>

              <Divider />

              <CardActions sx={{ p: 2 }}>
                <Button
                  variant={tier.buttonVariant}
                  color="primary"
                  fullWidth
                  onClick={() => handleSubscribe(tier.id)}
                  disabled={loading && selectedTier === tier.id}
                  size="large"
                >
                  {loading && selectedTier === tier.id ? (
                    <>
                      <CircularProgress size={20} sx={{ mr: 1 }} />
                      Processing...
                    </>
                  ) : (
                    tier.buttonText
                  )}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Comparison Table - Hidden on mobile, shown on tablet+ */}
      <Box sx={{ mt: 6, display: { xs: 'none', md: 'block' } }}>
        <Typography variant="h5" gutterBottom>
          Feature Comparison
        </Typography>

        <Paper sx={{ overflow: 'auto' }}>
          <Box sx={{ minWidth: 800 }}>
            <Grid container sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
              <Grid item xs={3} sx={{ p: 2, fontWeight: 'bold' }}></Grid>
              {subscriptionTiers.map((tier) => (
                <Grid item xs={3} key={tier.id} sx={{ p: 2, textAlign: 'center', fontWeight: 'bold' }}>
                  {tier.name}
                </Grid>
              ))}
            </Grid>

            {/* Basic Features */}
            <Grid container sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
              <Grid item xs={3} sx={{ p: 2, fontWeight: 'bold' }}>Basic Records Access</Grid>
              {subscriptionTiers.map((tier) => (
                <Grid item xs={3} key={tier.id} sx={{ p: 2, textAlign: 'center' }}>
                  {tier.features.includes('Access to basic records') || tier.features.includes('Access to all records') || tier.features.includes('Unlimited records access') ? <Check color="success" /> : <Close color="disabled" />}
                </Grid>
              ))}
            </Grid>

            {/* Advanced Search */}
            <Grid container sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
              <Grid item xs={3} sx={{ p: 2, fontWeight: 'bold' }}>Advanced Search Filters</Grid>
              {subscriptionTiers.map((tier) => (
                <Grid item xs={3} key={tier.id} sx={{ p: 2, textAlign: 'center' }}>
                  {tier.features.includes('Advanced search filters') ? <Check color="success" /> : <Close color="disabled" />}
                </Grid>
              ))}
            </Grid>

            {/* Export */}
            <Grid container sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
              <Grid item xs={3} sx={{ p: 2, fontWeight: 'bold' }}>Export Functionality</Grid>
              {subscriptionTiers.map((tier) => (
                <Grid item xs={3} key={tier.id} sx={{ p: 2, textAlign: 'center' }}>
                  {tier.features.includes('Export to CSV/Excel') || tier.features.includes('Export to multiple formats') ? <Check color="success" /> : <Close color="disabled" />}
                </Grid>
              ))}
            </Grid>

            {/* API Access */}
            <Grid container sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
              <Grid item xs={3} sx={{ p: 2, fontWeight: 'bold' }}>API Access</Grid>
              {subscriptionTiers.map((tier) => (
                <Grid item xs={3} key={tier.id} sx={{ p: 2, textAlign: 'center' }}>
                  {tier.features.includes('Basic API access') || tier.features.includes('Full API access') ? <Check color="success" /> : <Close color="disabled" />}
                </Grid>
              ))}
            </Grid>

            {/* Support */}
            <Grid container sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
              <Grid item xs={3} sx={{ p: 2, fontWeight: 'bold' }}>Priority Support</Grid>
              {subscriptionTiers.map((tier) => (
                <Grid item xs={3} key={tier.id} sx={{ p: 2, textAlign: 'center' }}>
                  {tier.features.includes('Priority support') ? <Check color="success" /> : <Close color="disabled" />}
                </Grid>
              ))}
            </Grid>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
};
