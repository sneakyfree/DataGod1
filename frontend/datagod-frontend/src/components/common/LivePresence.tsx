'use client';

import { useState, useEffect, useCallback } from 'react';
import { Box, Avatar, AvatarGroup, Tooltip, Typography, Chip } from '@mui/material';
import { Visibility } from '@mui/icons-material';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAuth } from '../../context/AuthContext';

interface Viewer {
    userId: string;
    username: string;
    fullName?: string;
    joinedAt: number;
}

interface LivePresenceProps {
    /** Unique room identifier, e.g. "record:123" or "entity:456" */
    roomId: string;
}

export default function LivePresence({ roomId }: LivePresenceProps) {
    const { user } = useAuth();
    const [viewers, setViewers] = useState<Viewer[]>([]);

    const handleMessage = useCallback(
        (msg: Record<string, any>) => {
            if (msg.event === 'presence_update' && msg.data?.room === roomId) {
                setViewers(msg.data.viewers || []);
            }
        },
        [roomId]
    );

    const { isConnected, sendMessage } = useWebSocket({
        userId: user?.id?.toString(),
        token: typeof window !== 'undefined' ? localStorage.getItem('access_token') || undefined : undefined,
        onMessage: handleMessage,
    });

    // Announce presence on connect
    useEffect(() => {
        if (isConnected && user) {
            sendMessage({
                event: 'join_room',
                room: roomId,
                user: {
                    userId: user.id,
                    username: user.username,
                    fullName: user.full_name,
                },
            });

            return () => {
                sendMessage({ event: 'leave_room', room: roomId });
            };
        }
    }, [isConnected, roomId, user, sendMessage]);

    // Filter out current user
    const otherViewers = viewers.filter(
        (v) => v.userId !== user?.id?.toString()
    );

    if (otherViewers.length === 0) return null;

    return (
        <Box
            sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                px: 1.5,
                py: 0.75,
                bgcolor: 'action.hover',
                borderRadius: 2,
            }}
        >
            <Chip
                icon={<Visibility sx={{ fontSize: 16 }} />}
                label={`${otherViewers.length} viewing`}
                size="small"
                color="info"
                variant="outlined"
            />
            <AvatarGroup max={4} sx={{ '& .MuiAvatar-root': { width: 28, height: 28, fontSize: '0.75rem' } }}>
                {otherViewers.map((v) => (
                    <Tooltip key={v.userId} title={v.fullName || v.username}>
                        <Avatar sx={{ bgcolor: 'primary.main' }}>
                            {(v.fullName || v.username || '?').charAt(0).toUpperCase()}
                        </Avatar>
                    </Tooltip>
                ))}
            </AvatarGroup>
        </Box>
    );
}
