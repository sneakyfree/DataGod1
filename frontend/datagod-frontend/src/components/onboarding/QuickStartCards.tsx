'use client';

import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardActionArea,
  Typography,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Chip,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import MapIcon from '@mui/icons-material/Map';
import HubIcon from '@mui/icons-material/Hub';
import PlayCircleIcon from '@mui/icons-material/PlayCircle';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { useRouter } from 'next/navigation';

interface QuickStartCard {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  action: () => void;
  tag?: string;
}

interface QuickStartCardsProps {
  onDismiss?: () => void;
}

export const QuickStartCards = ({ onDismiss }: QuickStartCardsProps) => {
  const router = useRouter();
  const [videoDialogOpen, setVideoDialogOpen] = useState(false);

  const cards: QuickStartCard[] = [
    {
      id: 'sample-search',
      title: 'Try a Sample Search',
      description: 'Search for "Smith" in Texas property records to see how it works',
      icon: <SearchIcon sx={{ fontSize: 32 }} />,
      color: '#1976d2',
      tag: 'Recommended',
      action: () => router.push('/search?q=Smith&state=TX'),
    },
    {
      id: 'explore-state',
      title: 'Explore Coverage',
      description: 'See which counties and record types are available in each state',
      icon: <MapIcon sx={{ fontSize: 32 }} />,
      color: '#388e3c',
      action: () => router.push('/jurisdictions'),
    },
    {
      id: 'entity-network',
      title: 'View Entity Network',
      description: 'Discover connections between people, companies, and properties',
      icon: <HubIcon sx={{ fontSize: 32 }} />,
      color: '#7b1fa2',
      action: () => router.push('/network'),
    },
    {
      id: 'watch-tutorial',
      title: 'Watch Quick Tutorial',
      description: 'Learn the key features in under 2 minutes',
      icon: <PlayCircleIcon sx={{ fontSize: 32 }} />,
      color: '#f57c00',
      action: () => setVideoDialogOpen(true),
    },
  ];

  return (
    <>
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h6" fontWeight={600}>
              Get Started
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Quick ways to explore what DataGod can do
            </Typography>
          </Box>
          {onDismiss && (
            <Button size="small" onClick={onDismiss} sx={{ color: 'text.secondary' }}>
              Dismiss
            </Button>
          )}
        </Box>

        <Grid container spacing={2}>
          {cards.map((card) => (
            <Grid item xs={12} sm={6} key={card.id}>
              <Card
                variant="outlined"
                sx={{
                  height: '100%',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    borderColor: card.color,
                    boxShadow: `0 4px 12px ${card.color}20`,
                    transform: 'translateY(-2px)',
                  },
                }}
              >
                <CardActionArea onClick={card.action} sx={{ height: '100%' }}>
                  <CardContent sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                    <Box
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        backgroundColor: `${card.color}15`,
                        color: card.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {card.icon}
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Typography variant="subtitle1" fontWeight={600}>
                          {card.title}
                        </Typography>
                        {card.tag && (
                          <Chip
                            label={card.tag}
                            size="small"
                            sx={{
                              height: 20,
                              fontSize: '0.65rem',
                              backgroundColor: `${card.color}20`,
                              color: card.color,
                            }}
                          />
                        )}
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {card.description}
                      </Typography>
                    </Box>
                    <ArrowForwardIcon sx={{ color: 'text.secondary', alignSelf: 'center' }} />
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Tutorial Video Dialog */}
      <Dialog
        open={videoDialogOpen}
        onClose={() => setVideoDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Quick Tutorial</DialogTitle>
        <DialogContent>
          <Box
            sx={{
              position: 'relative',
              paddingBottom: '56.25%',
              height: 0,
              overflow: 'hidden',
              backgroundColor: 'grey.100',
              borderRadius: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Placeholder for video - replace with actual video embed */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'grey.900',
                color: 'white',
              }}
            >
              <PlayCircleIcon sx={{ fontSize: 80, mb: 2, opacity: 0.8 }} />
              <Typography variant="h6" sx={{ opacity: 0.9 }}>
                Tutorial Video Coming Soon
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.7, mt: 1 }}>
                In the meantime, try our sample search to get started!
              </Typography>
            </Box>
          </Box>

          {/* Feature highlights */}
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2" gutterBottom fontWeight={600}>
              Key Features to Explore:
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <SearchIcon color="primary" fontSize="small" />
                  <Typography variant="body2">Advanced Search</Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <HubIcon color="secondary" fontSize="small" />
                  <Typography variant="body2">Entity Networks</Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TrendingUpIcon color="success" fontSize="small" />
                  <Typography variant="body2">Data Export</Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MapIcon color="warning" fontSize="small" />
                  <Typography variant="body2">Coverage Map</Typography>
                </Box>
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVideoDialogOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              setVideoDialogOpen(false);
              router.push('/search?q=Smith&state=TX');
            }}
          >
            Try Sample Search
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
