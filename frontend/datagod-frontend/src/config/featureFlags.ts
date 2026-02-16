/**
 * DataGod Feature Flag System
 * 
 * Reads feature flags from NEXT_PUBLIC_FEATURE_* environment variables.
 * All new features should be wrapped in feature flag checks.
 * 
 * Usage:
 *   import { featureFlag, useFeatureFlag } from '@/config/featureFlags';
 *   
 *   // In conditional rendering:
 *   {featureFlag('ml_dashboard') && <MLDashboard />}
 *   
 *   // In hooks:
 *   const isEnabled = useFeatureFlag('ml_dashboard');
 */

import { useMemo } from 'react';

export type FeatureFlagName =
    | 'ml_dashboard'
    | 'analytics'
    | 'real_time_updates'
    | 'entity_network'
    | 'comments'
    | 'notifications'
    | 'websocket'
    | 'scraper_monitoring'
    | 'data_quality'
    | 'explainability'
    | 'xml_export'
    | 'oauth';

/**
 * Registry of all feature flags with their env var names and defaults.
 * Flags default to true unless explicitly disabled (production-safe).
 */
const FLAG_REGISTRY: Record<FeatureFlagName, { envVar: string; defaultValue: boolean }> = {
    ml_dashboard: { envVar: 'NEXT_PUBLIC_FEATURE_ML_DASHBOARD', defaultValue: true },
    analytics: { envVar: 'NEXT_PUBLIC_FEATURE_ANALYTICS', defaultValue: true },
    real_time_updates: { envVar: 'NEXT_PUBLIC_FEATURE_REAL_TIME_UPDATES', defaultValue: false },
    entity_network: { envVar: 'NEXT_PUBLIC_FEATURE_ENTITY_NETWORK', defaultValue: true },
    comments: { envVar: 'NEXT_PUBLIC_FEATURE_COMMENTS', defaultValue: true },
    notifications: { envVar: 'NEXT_PUBLIC_FEATURE_NOTIFICATIONS', defaultValue: true },
    websocket: { envVar: 'NEXT_PUBLIC_FEATURE_WEBSOCKET', defaultValue: false },
    scraper_monitoring: { envVar: 'NEXT_PUBLIC_FEATURE_SCRAPER_MONITORING', defaultValue: true },
    data_quality: { envVar: 'NEXT_PUBLIC_FEATURE_DATA_QUALITY', defaultValue: true },
    explainability: { envVar: 'NEXT_PUBLIC_FEATURE_EXPLAINABILITY', defaultValue: true },
    xml_export: { envVar: 'NEXT_PUBLIC_FEATURE_XML_EXPORT', defaultValue: true },
    oauth: { envVar: 'NEXT_PUBLIC_FEATURE_OAUTH', defaultValue: false },
};

/**
 * Check if a feature flag is enabled.
 * Reads from environment variables at build time.
 */
export function featureFlag(name: FeatureFlagName): boolean {
    const flag = FLAG_REGISTRY[name];
    if (!flag) return false;

    const envValue = process.env[flag.envVar];
    if (envValue === undefined || envValue === '') return flag.defaultValue;

    return envValue === 'true' || envValue === '1';
}

/**
 * React hook for feature flag checks.
 * Memoized for performance.
 */
export function useFeatureFlag(name: FeatureFlagName): boolean {
    return useMemo(() => featureFlag(name), [name]);
}

/**
 * Get all feature flags and their current values.
 * Useful for debugging and admin panels.
 */
export function getAllFeatureFlags(): Record<FeatureFlagName, boolean> {
    const flags: Partial<Record<FeatureFlagName, boolean>> = {};
    for (const name of Object.keys(FLAG_REGISTRY) as FeatureFlagName[]) {
        flags[name] = featureFlag(name);
    }
    return flags as Record<FeatureFlagName, boolean>;
}
