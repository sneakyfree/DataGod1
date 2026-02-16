'use client';

import { useState, useCallback } from 'react';
import {
    Box,
    Typography,
    Container,
    Paper,
    List,
    ListItem,
    ListItemAvatar,
    ListItemText,
    Avatar,
    Chip,
    CircularProgress,
    Alert,
    Button,
    IconButton,
    Tooltip,
    Divider,
    Badge,
    Tabs,
    Tab,
    Switch,
    FormControlLabel,
} from '@mui/material';
import {
    Notifications as NotifIcon,
    NotificationsActive,
    Done,
    DoneAll,
    Refresh,
    Delete,
    Search,
    BugReport,
    Payment,
    Security,
    Info,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';
import { featureFlag } from '../../config/featureFlags';

function notifIcon(type: string) {
    switch (type) {
        case 'search': return <Search />;
        case 'anomaly': return <BugReport />;
        case 'payment': return <Payment />;
        case 'security': return <Security />;
        default: return <Info />;
    }
}

function notifColor(type: string): string {
    switch (type) {
        case 'anomaly': return '#d32f2f';
        case 'payment': return '#2e7d32';
        case 'security': return '#ed6c02';
        case 'search': return '#1976d2';
        default: return '#9e9e9e';
    }
}

interface TabPanelProps {
    children?: React.ReactNode;
    value: number;
    index: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
    return value === index ? <Box>{children}</Box> : null;
}

function NotificationsContent() {
    const [tab, setTab] = useState(0);
    const queryClient = useQueryClient();

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['notifications'],
        queryFn: () => apiService.get('/notifications').then((res: any) => res.data),
        staleTime: 15 * 1000,
    });

    const markRead = useMutation({
        mutationFn: (id: number) => apiService.put(`/notifications/${id}/read`, {}),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
    });

    const markAllRead = useMutation({
        mutationFn: () => apiService.put('/notifications/read-all', {}),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
    });

    const notifications = data?.notifications || data || [];
    const unreadCount = notifications.filter((n: any) => !n.read && !n.is_read).length;

    const allNotifs = notifications;
    const unreadNotifs = notifications.filter((n: any) => !n.read && !n.is_read);

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Badge badgeContent={unreadCount} color="error">
                            <NotifIcon />
                        </Badge>
                        Notifications
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Stay updated on anomalies, saved search results, and platform activity
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                        variant="outlined"
                        size="small"
                        startIcon={<DoneAll />}
                        onClick={() => markAllRead.mutate()}
                        disabled={unreadCount === 0}
                    >
                        Mark All Read
                    </Button>
                    <Tooltip title="Refresh">
                        <IconButton onClick={() => refetch()}>
                            <Refresh />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            {error && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Notification service may not be active. Showing cached data.
                </Alert>
            )}

            <Paper>
                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
                    <Tab label={`All (${allNotifs.length})`} />
                    <Tab label={`Unread (${unreadCount})`} />
                </Tabs>

                <TabPanel value={tab} index={0}>
                    <NotificationList
                        notifications={allNotifs}
                        isLoading={isLoading}
                        onMarkRead={(id) => markRead.mutate(id)}
                    />
                </TabPanel>

                <TabPanel value={tab} index={1}>
                    <NotificationList
                        notifications={unreadNotifs}
                        isLoading={isLoading}
                        onMarkRead={(id) => markRead.mutate(id)}
                    />
                </TabPanel>
            </Paper>
        </Container>
    );
}

function NotificationList({
    notifications,
    isLoading,
    onMarkRead,
}: {
    notifications: any[];
    isLoading: boolean;
    onMarkRead: (id: number) => void;
}) {
    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (notifications.length === 0) {
        return (
            <Box sx={{ textAlign: 'center', py: 4 }}>
                <NotificationsActive sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
                <Typography color="text.secondary">No notifications</Typography>
            </Box>
        );
    }

    return (
        <List disablePadding>
            {notifications.map((notif: any, idx: number) => (
                <Box key={notif.id || idx}>
                    <ListItem
                        sx={{
                            opacity: notif.read || notif.is_read ? 0.7 : 1,
                            bgcolor: notif.read || notif.is_read ? 'transparent' : 'action.hover',
                        }}
                        secondaryAction={
                            !notif.read && !notif.is_read ? (
                                <Tooltip title="Mark as read">
                                    <IconButton size="small" onClick={() => onMarkRead(notif.id)}>
                                        <Done />
                                    </IconButton>
                                </Tooltip>
                            ) : null
                        }
                    >
                        <ListItemAvatar>
                            <Avatar sx={{ bgcolor: notifColor(notif.type || notif.notification_type) }}>
                                {notifIcon(notif.type || notif.notification_type)}
                            </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                            primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Typography variant="body1" fontWeight={notif.read || notif.is_read ? 400 : 600}>
                                        {notif.title || notif.message}
                                    </Typography>
                                    <Chip
                                        label={notif.type || notif.notification_type || 'info'}
                                        size="small"
                                        variant="outlined"
                                    />
                                </Box>
                            }
                            secondary={
                                <Box>
                                    {notif.body && (
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                                            {notif.body}
                                        </Typography>
                                    )}
                                    <Typography variant="caption" color="text.disabled">
                                        {notif.created_at ? new Date(notif.created_at).toLocaleString() : '—'}
                                    </Typography>
                                </Box>
                            }
                        />
                    </ListItem>
                    {idx < notifications.length - 1 && <Divider />}
                </Box>
            ))}
        </List>
    );
}

export default function NotificationsPage() {
    if (!featureFlag('notifications')) {
        return (
            <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
                <Typography variant="h5" color="text.secondary">
                    Notifications are coming soon
                </Typography>
            </Container>
        );
    }

    return (
        <ProtectedRoute>
            <NotificationsContent />
        </ProtectedRoute>
    );
}
