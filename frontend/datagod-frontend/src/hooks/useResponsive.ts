'use client';

import { useState, useEffect, useCallback } from 'react';
import { useMediaQuery, useTheme } from '@mui/material';

// =============================================================================
// BREAKPOINT DEFINITIONS
// =============================================================================

export const breakpoints = {
    xs: 0,
    sm: 600,
    md: 900,
    lg: 1200,
    xl: 1536,
} as const;

export type Breakpoint = keyof typeof breakpoints;

// =============================================================================
// TYPES
// =============================================================================

export interface DeviceInfo {
    isMobile: boolean;
    isTablet: boolean;
    isDesktop: boolean;
    isLargeDesktop: boolean;
    breakpoint: Breakpoint;
    width: number;
    height: number;
    orientation: 'portrait' | 'landscape';
    isTouchDevice: boolean;
    isStandalone: boolean; // PWA mode
}

export interface ResponsiveValue<T> {
    xs?: T;
    sm?: T;
    md?: T;
    lg?: T;
    xl?: T;
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook to detect current device information and responsive state
 */
export function useDevice(): DeviceInfo {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
    const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'md'));
    const isDesktop = useMediaQuery(theme.breakpoints.between('md', 'lg'));
    const isLargeDesktop = useMediaQuery(theme.breakpoints.up('lg'));

    const [windowSize, setWindowSize] = useState({
        width: typeof window !== 'undefined' ? window.innerWidth : 1200,
        height: typeof window !== 'undefined' ? window.innerHeight : 800,
    });

    const [isTouchDevice, setIsTouchDevice] = useState(false);
    const [isStandalone, setIsStandalone] = useState(false);

    useEffect(() => {
        const handleResize = () => {
            setWindowSize({
                width: window.innerWidth,
                height: window.innerHeight,
            });
        };

        // Check for touch device
        setIsTouchDevice(
            'ontouchstart' in window ||
            navigator.maxTouchPoints > 0
        );

        // Check for PWA standalone mode
        setIsStandalone(
            window.matchMedia('(display-mode: standalone)').matches ||
            (window.navigator as any).standalone === true
        );

        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Determine current breakpoint
    const getBreakpoint = (): Breakpoint => {
        if (windowSize.width < breakpoints.sm) return 'xs';
        if (windowSize.width < breakpoints.md) return 'sm';
        if (windowSize.width < breakpoints.lg) return 'md';
        if (windowSize.width < breakpoints.xl) return 'lg';
        return 'xl';
    };

    return {
        isMobile,
        isTablet,
        isDesktop,
        isLargeDesktop,
        breakpoint: getBreakpoint(),
        width: windowSize.width,
        height: windowSize.height,
        orientation: windowSize.width > windowSize.height ? 'landscape' : 'portrait',
        isTouchDevice,
        isStandalone,
    };
}

/**
 * Hook for responsive values based on breakpoint
 */
export function useResponsiveValue<T>(values: ResponsiveValue<T>, defaultValue: T): T {
    const { breakpoint } = useDevice();

    const breakpointOrder: Breakpoint[] = ['xs', 'sm', 'md', 'lg', 'xl'];
    const currentIndex = breakpointOrder.indexOf(breakpoint);

    // Find the closest defined value at or below current breakpoint
    for (let i = currentIndex; i >= 0; i--) {
        const key = breakpointOrder[i];
        if (values[key] !== undefined) {
            return values[key] as T;
        }
    }

    return defaultValue;
}

/**
 * Hook for mobile navigation state
 */
export function useMobileNav() {
    const [isOpen, setIsOpen] = useState(false);
    const { isMobile, isTablet } = useDevice();

    const open = useCallback(() => setIsOpen(true), []);
    const close = useCallback(() => setIsOpen(false), []);
    const toggle = useCallback(() => setIsOpen(prev => !prev), []);

    // Auto-close on desktop
    useEffect(() => {
        if (!isMobile && !isTablet && isOpen) {
            setIsOpen(false);
        }
    }, [isMobile, isTablet, isOpen]);

    return {
        isOpen,
        open,
        close,
        toggle,
        shouldShowMobileNav: isMobile || isTablet,
    };
}

/**
 * Hook for swipe gestures (mobile)
 */
export function useSwipe(
    onSwipeLeft?: () => void,
    onSwipeRight?: () => void,
    onSwipeUp?: () => void,
    onSwipeDown?: () => void,
    threshold = 50
) {
    const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);

    const handleTouchStart = useCallback((e: React.TouchEvent) => {
        setTouchStart({
            x: e.touches[0].clientX,
            y: e.touches[0].clientY,
        });
    }, []);

    const handleTouchEnd = useCallback((e: React.TouchEvent) => {
        if (!touchStart) return;

        const touchEnd = {
            x: e.changedTouches[0].clientX,
            y: e.changedTouches[0].clientY,
        };

        const diffX = touchStart.x - touchEnd.x;
        const diffY = touchStart.y - touchEnd.y;

        // Horizontal swipe
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > threshold) {
            if (diffX > 0) {
                onSwipeLeft?.();
            } else {
                onSwipeRight?.();
            }
        }
        // Vertical swipe
        else if (Math.abs(diffY) > threshold) {
            if (diffY > 0) {
                onSwipeUp?.();
            } else {
                onSwipeDown?.();
            }
        }

        setTouchStart(null);
    }, [touchStart, threshold, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown]);

    return {
        onTouchStart: handleTouchStart,
        onTouchEnd: handleTouchEnd,
    };
}

/**
 * Hook for safe area insets (notch handling)
 */
export function useSafeAreaInsets() {
    const [insets, setInsets] = useState({
        top: 0,
        right: 0,
        bottom: 0,
        left: 0,
    });

    useEffect(() => {
        const updateInsets = () => {
            const style = getComputedStyle(document.documentElement);
            setInsets({
                top: parseInt(style.getPropertyValue('--sat') || '0'),
                right: parseInt(style.getPropertyValue('--sar') || '0'),
                bottom: parseInt(style.getPropertyValue('--sab') || '0'),
                left: parseInt(style.getPropertyValue('--sal') || '0'),
            });
        };

        updateInsets();
        window.addEventListener('resize', updateInsets);
        return () => window.removeEventListener('resize', updateInsets);
    }, []);

    return insets;
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get responsive spacing value
 */
export function getResponsiveSpacing(
    base: number,
    breakpoint: Breakpoint
): number {
    const multipliers: Record<Breakpoint, number> = {
        xs: 0.75,
        sm: 0.875,
        md: 1,
        lg: 1.125,
        xl: 1.25,
    };
    return Math.round(base * multipliers[breakpoint]);
}

/**
 * Get responsive font size
 */
export function getResponsiveFontSize(
    base: number,
    breakpoint: Breakpoint
): string {
    const scales: Record<Breakpoint, number> = {
        xs: 0.875,
        sm: 0.9375,
        md: 1,
        lg: 1.0625,
        xl: 1.125,
    };
    return `${base * scales[breakpoint]}rem`;
}

/**
 * Generate responsive grid columns
 */
export function getResponsiveColumns(
    breakpoint: Breakpoint,
    config: ResponsiveValue<number> = {}
): number {
    const defaults: ResponsiveValue<number> = {
        xs: 1,
        sm: 2,
        md: 3,
        lg: 4,
        xl: 6,
    };

    return config[breakpoint] ?? defaults[breakpoint] ?? 1;
}

export default useDevice;
