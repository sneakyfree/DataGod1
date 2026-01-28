'use client';

import React from 'react';
import { IconButton, Tooltip, useTheme } from '@mui/material';
import { DarkMode, LightMode } from '@mui/icons-material';
import { useThemeMode } from '../../context/ThemeContext';

interface ThemeToggleProps {
    size?: 'small' | 'medium' | 'large';
    showTooltip?: boolean;
}

/**
 * Theme toggle button component for switching between light and dark modes.
 * Uses the ThemeContext to manage theme state.
 */
export default function ThemeToggle({
    size = 'medium',
    showTooltip = true
}: ThemeToggleProps) {
    const { mode, toggleTheme } = useThemeMode();
    const theme = useTheme();

    const isDark = mode === 'dark';
    const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';

    const button = (
        <IconButton
            onClick={toggleTheme}
            size={size}
            aria-label={label}
            sx={{
                color: theme.palette.text.primary,
                transition: 'transform 0.3s ease, color 0.3s ease',
                '&:hover': {
                    transform: 'rotate(180deg)',
                    backgroundColor: theme.palette.action.hover,
                },
            }}
        >
            {isDark ? (
                <LightMode
                    sx={{
                        color: '#ffc107',
                        filter: 'drop-shadow(0 0 4px rgba(255, 193, 7, 0.5))',
                    }}
                />
            ) : (
                <DarkMode
                    sx={{
                        color: '#5c6bc0',
                        filter: 'drop-shadow(0 0 4px rgba(92, 107, 192, 0.3))',
                    }}
                />
            )}
        </IconButton>
    );

    if (showTooltip) {
        return (
            <Tooltip title={label} arrow>
                {button}
            </Tooltip>
        );
    }

    return button;
}
