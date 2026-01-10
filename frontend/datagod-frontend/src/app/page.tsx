'use client';

import { Box } from '@mui/material';
import {
  HeroSection,
  FeatureShowcase,
  StatsCounter,
  SampleSearch,
  CallToAction,
} from '../components/landing';

export default function LandingPage() {
  return (
    <Box sx={{ minHeight: '100vh' }}>
      <HeroSection />
      <StatsCounter />
      <FeatureShowcase />
      <SampleSearch />
      <CallToAction />
    </Box>
  );
}
