'use client';

import { Box, Typography, Container, Grid } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

interface CounterProps {
  end: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
}

const AnimatedCounter = ({ end, duration = 2000, suffix = '', prefix = '' }: CounterProps) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);

      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      setCount(Math.floor(easeOutQuart * end));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [end, duration]);

  return (
    <Typography
      sx={{
        fontSize: { xs: '2.5rem', sm: '3rem', md: '3.5rem' },
        fontWeight: 800,
        color: 'primary.main',
      }}
    >
      {prefix}{count.toLocaleString()}{suffix}
    </Typography>
  );
};

export const StatsCounter = () => {
  // This could fetch from a public API endpoint
  const stats = {
    totalRecords: 12847293,
    statesCovered: 50,
    countiesCovered: 3142,
    recordTypes: 6,
  };

  const statItems = [
    {
      value: stats.totalRecords,
      label: 'Public Records',
      suffix: '+',
      description: 'Searchable documents',
    },
    {
      value: stats.statesCovered,
      label: 'States Covered',
      suffix: '',
      description: 'Plus territories',
    },
    {
      value: stats.countiesCovered,
      label: 'Counties',
      suffix: '+',
      description: 'Coverage areas',
    },
    {
      value: stats.recordTypes,
      label: 'Document Types',
      suffix: '',
      description: 'Categories tracked',
    },
  ];

  return (
    <Box
      sx={{
        py: { xs: 8, md: 10 },
        backgroundColor: 'white',
      }}
    >
      <Container maxWidth="lg">
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography
            variant="h2"
            sx={{
              fontSize: { xs: '1.75rem', sm: '2rem', md: '2.5rem' },
              fontWeight: 700,
              mb: 2,
            }}
          >
            The Numbers Speak
          </Typography>
          <Typography
            variant="body1"
            sx={{
              fontSize: { xs: '1rem', md: '1.125rem' },
              color: 'text.secondary',
              maxWidth: 500,
              mx: 'auto',
            }}
          >
            America&apos;s most comprehensive public records database, growing every day
          </Typography>
        </Box>

        <Grid container spacing={4}>
          {statItems.map((stat) => (
            <Grid item xs={6} md={3} key={stat.label}>
              <Box
                sx={{
                  textAlign: 'center',
                  p: 3,
                  borderRadius: 3,
                  backgroundColor: 'grey.50',
                  transition: 'background-color 0.2s',
                  '&:hover': {
                    backgroundColor: 'primary.light',
                    '& .stat-value': {
                      color: 'white',
                    },
                    '& .stat-label': {
                      color: 'white',
                    },
                    '& .stat-desc': {
                      color: 'rgba(255,255,255,0.8)',
                    },
                  },
                }}
              >
                <Box className="stat-value">
                  <AnimatedCounter end={stat.value} suffix={stat.suffix} />
                </Box>
                <Typography
                  className="stat-label"
                  variant="h6"
                  sx={{
                    fontWeight: 600,
                    mb: 0.5,
                    transition: 'color 0.2s',
                  }}
                >
                  {stat.label}
                </Typography>
                <Typography
                  className="stat-desc"
                  variant="body2"
                  sx={{
                    color: 'text.secondary',
                    transition: 'color 0.2s',
                  }}
                >
                  {stat.description}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};
