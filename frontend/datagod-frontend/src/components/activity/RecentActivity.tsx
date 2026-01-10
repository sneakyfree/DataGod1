'use client';

import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Skeleton,
  Alert,
  Chip,
  Divider,
  Button,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import DescriptionIcon from '@mui/icons-material/Description';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import HomeIcon from '@mui/icons-material/Home';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import VisibilityIcon from '@mui/icons-material/Visibility';
import HistoryIcon from '@mui/icons-material/History';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiService } from '../../services/api';

interface Activity {
  id: number;
  activity_type: string;
  record_id?: number;
  entity_id?: number;
  search_id?: number;
  activity_data?: {
    query?: string;
    record_title?: string;
    entity_name?: string;
    export_format?: string;
  };
  created_at: string;
}

interface RecentActivityProps {
  limit?: number;
  showHeader?: boolean;
}

const activityTypeConfig: Record<string, {
  icon: React.ReactNode;
  label: string;
  color: string;
}> = {
  search: {
    icon: <SearchIcon />,
    label: 'Search',
    color: '#1976d2',
  },
  view_record: {
    icon: <DescriptionIcon />,
    label: 'Viewed',
    color: '#388e3c',
  },
  view_entity: {
    icon: <PersonIcon />,
    label: 'Viewed Entity',
    color: '#7b1fa2',
  },
  save_search: {
    icon: <BookmarkIcon />,
    label: 'Saved Search',
    color: '#f57c00',
  },
  export: {
    icon: <FileDownloadIcon />,
    label: 'Export',
    color: '#0288d1',
  },
  run_saved_search: {
    icon: <HistoryIcon />,
    label: 'Ran Search',
    color: '#00838f',
  },
};

const getEntityIcon = (type?: string) => {
  switch (type?.toLowerCase()) {
    case 'person':
      return <PersonIcon />;
    case 'company':
      return <BusinessIcon />;
    case 'property':
      return <HomeIcon />;
    default:
      return <PersonIcon />;
  }
};

export const RecentActivity = ({ limit = 10, showHeader = true }: RecentActivityProps) => {
  const router = useRouter();

  const { data: activities, isLoading, error } = useQuery({
    queryKey: ['recentActivities', limit],
    queryFn: () => apiService.getRecentActivities({ limit }).then(res => res.data),
    staleTime: 60 * 1000,
  });

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getActivityDescription = (activity: Activity) => {
    switch (activity.activity_type) {
      case 'search':
        return activity.activity_data?.query
          ? `Searched for "${activity.activity_data.query}"`
          : 'Performed a search';
      case 'view_record':
        return activity.activity_data?.record_title
          ? `Viewed: ${activity.activity_data.record_title}`
          : `Viewed record #${activity.record_id}`;
      case 'view_entity':
        return activity.activity_data?.entity_name
          ? `Viewed: ${activity.activity_data.entity_name}`
          : `Viewed entity #${activity.entity_id}`;
      case 'save_search':
        return 'Saved a search query';
      case 'export':
        return activity.activity_data?.export_format
          ? `Exported data as ${activity.activity_data.export_format.toUpperCase()}`
          : 'Exported data';
      case 'run_saved_search':
        return 'Ran a saved search';
      default:
        return 'Activity recorded';
    }
  };

  const handleActivityClick = (activity: Activity) => {
    if (activity.record_id) {
      router.push(`/records/${activity.record_id}`);
    } else if (activity.entity_id) {
      router.push(`/network?entityId=${activity.entity_id}`);
    } else if (activity.search_id) {
      router.push('/saved');
    } else if (activity.activity_type === 'search' && activity.activity_data?.query) {
      router.push(`/search?q=${encodeURIComponent(activity.activity_data.query)}`);
    }
  };

  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        {showHeader && (
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Recent Activity
          </Typography>
        )}
        {[1, 2, 3, 4, 5].map((i) => (
          <Box key={i} sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Skeleton variant="circular" width={40} height={40} />
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="30%" />
            </Box>
          </Box>
        ))}
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        {showHeader && (
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Recent Activity
          </Typography>
        )}
        <Alert severity="warning">Unable to load recent activity</Alert>
      </Paper>
    );
  }

  const activityList = activities || [];

  return (
    <Paper sx={{ p: 0, overflow: 'hidden' }}>
      {showHeader && (
        <Box sx={{ p: 2, pb: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Recent Activity
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {activityList.length} items
          </Typography>
        </Box>
      )}

      {activityList.length === 0 ? (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <HistoryIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
          <Typography variant="body1" color="text.secondary">
            No recent activity
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Your search and browsing history will appear here
          </Typography>
          <Button
            variant="outlined"
            startIcon={<SearchIcon />}
            onClick={() => router.push('/search')}
            size="small"
          >
            Start Searching
          </Button>
        </Box>
      ) : (
        <List disablePadding>
          {activityList.map((activity: Activity, index: number) => {
            const config = activityTypeConfig[activity.activity_type] || {
              icon: <VisibilityIcon />,
              label: 'Activity',
              color: '#616161',
            };

            return (
              <ListItem key={activity.id} disablePadding divider={index < activityList.length - 1}>
                <ListItemButton
                  onClick={() => handleActivityClick(activity)}
                  sx={{ px: 2, py: 1.5 }}
                >
                  <ListItemIcon sx={{ minWidth: 44, color: config.color }}>
                    {config.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                          {getActivityDescription(activity)}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                        <Chip
                          label={config.label}
                          size="small"
                          sx={{
                            height: 18,
                            fontSize: '0.65rem',
                            backgroundColor: `${config.color}15`,
                            color: config.color,
                          }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {formatTimeAgo(activity.created_at)}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      )}
    </Paper>
  );
};
