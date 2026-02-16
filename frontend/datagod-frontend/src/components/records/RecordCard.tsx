'use client';

import React from 'react';
import {
    Card,
    CardContent,
    CardActions,
    Typography,
    Chip,
    Box,
    IconButton,
    Tooltip,
} from '@mui/material';
import {
    Favorite,
    FavoriteBorder,
    Share,
    Download,
    OpenInNew,
    CalendarToday,
    AttachMoney,
    LocationOn,
} from '@mui/icons-material';
import Link from 'next/link';

interface RecordCardProps {
    record: {
        id: number;
        title: string;
        description?: string;
        record_type?: string;
        amount?: number;
        date?: string;
        jurisdiction_name?: string;
        jurisdiction_id?: number;
        source?: string;
        [key: string]: any;
    };
    isFavorite?: boolean;
    onFavorite?: (recordId: number) => void;
    onShare?: (recordId: number) => void;
    onExport?: (recordId: number) => void;
    compact?: boolean;
}

function typeColor(type: string): 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'default' {
    switch (type?.toLowerCase()) {
        case 'business_filing':
        case 'annual_report':
            return 'primary';
        case 'ucc':
        case 'lien':
            return 'warning';
        case 'court':
        case 'judgment':
            return 'info';
        case 'property':
        case 'deed':
            return 'success';
        default:
            return 'default';
    }
}

export default function RecordCard({
    record,
    isFavorite = false,
    onFavorite,
    onShare,
    onExport,
    compact = false,
}: RecordCardProps) {
    return (
        <Card
            variant="outlined"
            sx={{
                transition: 'box-shadow 0.2s, transform 0.15s',
                '&:hover': {
                    boxShadow: 3,
                    transform: 'translateY(-1px)',
                },
            }}
        >
            <CardContent sx={{ pb: compact ? 1 : 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Link href={`/records/${record.id}`} style={{ textDecoration: 'none', color: 'inherit', flex: 1 }}>
                        <Typography
                            variant={compact ? 'body1' : 'h6'}
                            fontWeight={600}
                            sx={{
                                cursor: 'pointer',
                                '&:hover': { color: 'primary.main' },
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                overflow: 'hidden',
                            }}
                        >
                            {record.title || 'Untitled Record'}
                        </Typography>
                    </Link>
                    {record.record_type && (
                        <Chip
                            label={record.record_type.replace(/_/g, ' ')}
                            size="small"
                            color={typeColor(record.record_type)}
                            sx={{ ml: 1, flexShrink: 0, textTransform: 'capitalize' }}
                        />
                    )}
                </Box>

                {!compact && record.description && (
                    <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{
                            mb: 1.5,
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                        }}
                    >
                        {record.description}
                    </Typography>
                )}

                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                    {record.date && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <CalendarToday sx={{ fontSize: 14, color: 'text.disabled' }} />
                            <Typography variant="caption" color="text.secondary">
                                {new Date(record.date).toLocaleDateString()}
                            </Typography>
                        </Box>
                    )}

                    {record.amount != null && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <AttachMoney sx={{ fontSize: 14, color: 'text.disabled' }} />
                            <Typography variant="caption" color="text.secondary">
                                {record.amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                            </Typography>
                        </Box>
                    )}

                    {record.jurisdiction_name && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <LocationOn sx={{ fontSize: 14, color: 'text.disabled' }} />
                            <Typography variant="caption" color="text.secondary">
                                {record.jurisdiction_name}
                            </Typography>
                        </Box>
                    )}
                </Box>
            </CardContent>

            <CardActions sx={{ px: 2, pt: 0, justifyContent: 'flex-end' }}>
                {onFavorite && (
                    <Tooltip title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}>
                        <IconButton size="small" onClick={() => onFavorite(record.id)}>
                            {isFavorite ? <Favorite color="error" fontSize="small" /> : <FavoriteBorder fontSize="small" />}
                        </IconButton>
                    </Tooltip>
                )}
                {onShare && (
                    <Tooltip title="Share">
                        <IconButton size="small" onClick={() => onShare(record.id)}>
                            <Share fontSize="small" />
                        </IconButton>
                    </Tooltip>
                )}
                {onExport && (
                    <Tooltip title="Export">
                        <IconButton size="small" onClick={() => onExport(record.id)}>
                            <Download fontSize="small" />
                        </IconButton>
                    </Tooltip>
                )}
                <Tooltip title="View details">
                    <Link href={`/records/${record.id}`}>
                        <IconButton size="small">
                            <OpenInNew fontSize="small" />
                        </IconButton>
                    </Link>
                </Tooltip>
            </CardActions>
        </Card>
    );
}
