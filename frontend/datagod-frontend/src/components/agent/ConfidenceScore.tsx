'use client';

import React from 'react';
import {
    Box,
    Typography,
    Tooltip,
    LinearProgress,
    Chip,
    useTheme,
    alpha,
} from '@mui/material';
import {
    CheckCircle as HighIcon,
    Warning as MediumIcon,
    Error as LowIcon,
    HelpOutline as UnknownIcon,
} from '@mui/icons-material';

// =============================================================================
// TYPES
// =============================================================================

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'unknown';

export interface ConfidenceBreakdown {
    factor: string;
    score: number;
    weight: number;
    description?: string;
}

export interface ConfidenceScoreProps {
    score: number; // 0-1
    breakdown?: ConfidenceBreakdown[];
    showLabel?: boolean;
    showIcon?: boolean;
    size?: 'small' | 'medium' | 'large';
    variant?: 'linear' | 'circular' | 'chip' | 'badge';
    animated?: boolean;
    onClick?: () => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const getConfidenceLevel = (score: number): ConfidenceLevel => {
    if (score >= 0.85) return 'high';
    if (score >= 0.65) return 'medium';
    if (score >= 0) return 'low';
    return 'unknown';
};

const confidenceConfig: Record<ConfidenceLevel, { color: string; label: string; icon: React.ReactNode }> = {
    high: { color: '#4caf50', label: 'High Confidence', icon: <HighIcon /> },
    medium: { color: '#ff9800', label: 'Medium Confidence', icon: <MediumIcon /> },
    low: { color: '#f44336', label: 'Low Confidence', icon: <LowIcon /> },
    unknown: { color: '#9e9e9e', label: 'Unknown', icon: <UnknownIcon /> },
};

const sizeConfig = {
    small: { height: 4, fontSize: '0.75rem', iconSize: 16, padding: 0.5 },
    medium: { height: 8, fontSize: '0.875rem', iconSize: 20, padding: 1 },
    large: { height: 12, fontSize: '1rem', iconSize: 24, padding: 1.5 },
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function ConfidenceScore({
    score,
    breakdown,
    showLabel = true,
    showIcon = true,
    size = 'medium',
    variant = 'linear',
    animated = true,
    onClick,
}: ConfidenceScoreProps) {
    const theme = useTheme();
    const level = getConfidenceLevel(score);
    const config = confidenceConfig[level];
    const sizes = sizeConfig[size];
    const percentage = Math.round(score * 100);

    // Tooltip content with breakdown
    const tooltipContent = (
        <Box sx={{ p: 1, maxWidth: 280 }}>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                {config.label}: {percentage}%
            </Typography>
            {breakdown && breakdown.length > 0 && (
                <>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                        Score Breakdown:
                    </Typography>
                    {breakdown.map((item, idx) => (
                        <Box key={idx} sx={{ mb: 0.5 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.25 }}>
                                <Typography variant="caption">{item.factor}</Typography>
                                <Typography variant="caption" fontWeight={600}>
                                    {Math.round(item.score * 100)}% (×{item.weight})
                                </Typography>
                            </Box>
                            <LinearProgress
                                variant="determinate"
                                value={item.score * 100}
                                sx={{
                                    height: 3,
                                    borderRadius: 1.5,
                                    backgroundColor: alpha(config.color, 0.2),
                                    '& .MuiLinearProgress-bar': {
                                        backgroundColor: config.color,
                                    },
                                }}
                            />
                            {item.description && (
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                                    {item.description}
                                </Typography>
                            )}
                        </Box>
                    ))}
                </>
            )}
        </Box>
    );

    // Linear variant (progress bar)
    if (variant === 'linear') {
        return (
            <Tooltip title={tooltipContent} arrow placement="top">
                <Box
                    onClick={onClick}
                    sx={{
                        cursor: onClick ? 'pointer' : 'default',
                        '&:hover': onClick ? { opacity: 0.8 } : {},
                    }}
                >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        {showIcon && (
                            <Box
                                sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    color: config.color,
                                    '& svg': { fontSize: sizes.iconSize },
                                }}
                            >
                                {config.icon}
                            </Box>
                        )}
                        {showLabel && (
                            <Typography variant="caption" sx={{ fontSize: sizes.fontSize, fontWeight: 600 }}>
                                {percentage}%
                            </Typography>
                        )}
                    </Box>
                    <LinearProgress
                        variant="determinate"
                        value={percentage}
                        sx={{
                            height: sizes.height,
                            borderRadius: sizes.height / 2,
                            backgroundColor: alpha(config.color, 0.15),
                            '& .MuiLinearProgress-bar': {
                                backgroundColor: config.color,
                                borderRadius: sizes.height / 2,
                                transition: animated ? 'transform 0.6s ease' : 'none',
                            },
                        }}
                    />
                </Box>
            </Tooltip>
        );
    }

    // Circular variant (ring progress)
    if (variant === 'circular') {
        const circleSize = size === 'small' ? 40 : size === 'medium' ? 60 : 80;
        const strokeWidth = size === 'small' ? 3 : size === 'medium' ? 4 : 6;
        const radius = (circleSize - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (score * circumference);

        return (
            <Tooltip title={tooltipContent} arrow placement="top">
                <Box
                    onClick={onClick}
                    sx={{
                        position: 'relative',
                        width: circleSize,
                        height: circleSize,
                        cursor: onClick ? 'pointer' : 'default',
                        '&:hover': onClick ? { opacity: 0.8 } : {},
                    }}
                >
                    <svg width={circleSize} height={circleSize}>
                        {/* Background circle */}
                        <circle
                            cx={circleSize / 2}
                            cy={circleSize / 2}
                            r={radius}
                            fill="none"
                            stroke={alpha(config.color, 0.15)}
                            strokeWidth={strokeWidth}
                        />
                        {/* Progress circle */}
                        <circle
                            cx={circleSize / 2}
                            cy={circleSize / 2}
                            r={radius}
                            fill="none"
                            stroke={config.color}
                            strokeWidth={strokeWidth}
                            strokeLinecap="round"
                            strokeDasharray={circumference}
                            strokeDashoffset={offset}
                            style={{
                                transform: 'rotate(-90deg)',
                                transformOrigin: '50% 50%',
                                transition: animated ? 'stroke-dashoffset 0.6s ease' : 'none',
                            }}
                        />
                    </svg>
                    {/* Center content */}
                    <Box
                        sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        {showIcon && (
                            <Box sx={{ color: config.color, '& svg': { fontSize: sizes.iconSize } }}>
                                {config.icon}
                            </Box>
                        )}
                        {showLabel && !showIcon && (
                            <Typography
                                variant="caption"
                                sx={{
                                    fontSize: sizes.fontSize,
                                    fontWeight: 700,
                                    color: config.color,
                                }}
                            >
                                {percentage}%
                            </Typography>
                        )}
                    </Box>
                </Box>
            </Tooltip>
        );
    }

    // Chip variant
    if (variant === 'chip') {
        return (
            <Tooltip title={tooltipContent} arrow placement="top">
                <Chip
                    icon={showIcon ? config.icon as React.ReactElement : undefined}
                    label={showLabel ? `${percentage}%` : config.label}
                    size={size === 'large' ? 'medium' : 'small'}
                    onClick={onClick}
                    sx={{
                        backgroundColor: alpha(config.color, 0.1),
                        color: config.color,
                        fontWeight: 600,
                        '& .MuiChip-icon': { color: config.color },
                        cursor: onClick ? 'pointer' : 'default',
                    }}
                />
            </Tooltip>
        );
    }

    // Badge variant (just the number)
    if (variant === 'badge') {
        return (
            <Tooltip title={tooltipContent} arrow placement="top">
                <Box
                    onClick={onClick}
                    sx={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        px: sizes.padding,
                        py: sizes.padding / 2,
                        borderRadius: 1,
                        backgroundColor: alpha(config.color, 0.1),
                        color: config.color,
                        cursor: onClick ? 'pointer' : 'default',
                        '&:hover': onClick ? { backgroundColor: alpha(config.color, 0.2) } : {},
                    }}
                >
                    {showIcon && (
                        <Box sx={{ mr: 0.5, display: 'flex', '& svg': { fontSize: sizes.iconSize } }}>
                            {config.icon}
                        </Box>
                    )}
                    <Typography variant="caption" sx={{ fontSize: sizes.fontSize, fontWeight: 700 }}>
                        {percentage}%
                    </Typography>
                </Box>
            </Tooltip>
        );
    }

    return null;
}

// =============================================================================
// EXPORTS
// =============================================================================

export { getConfidenceLevel, confidenceConfig };
