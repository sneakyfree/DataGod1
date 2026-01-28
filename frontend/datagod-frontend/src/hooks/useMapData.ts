'use client';

import { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';

export interface StateMapData {
    stateCode: string;
    stateName: string;
    value: number;
    metadata: {
        jurisdictions: number;
        activeJurisdictions: number;
        records: number;
        coverage: number;
        lastUpdated: string | null;
        tier: number;
    };
}

export interface CountyMapData {
    fips: string;
    name: string;
    stateCode: string;
    value: number;
    metadata: {
        records: number;
        coverage: number;
        dataCategories: string[];
    };
}

export interface MapFilters {
    tier?: number;
    minCoverage?: number;
    stateCode?: string;
}

export interface UseMapDataOptions {
    level?: 'state' | 'county';
    metric?: 'coverage' | 'records' | 'activity';
    filters?: MapFilters;
    enabled?: boolean;
}

// State names lookup
const STATE_NAMES: Record<string, string> = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
    'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine',
    'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska',
    'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
    'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island',
    'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas',
    'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
    'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'PR': 'Puerto Rico',
};

export function useMapData(options: UseMapDataOptions = {}) {
    const { level = 'state', metric = 'coverage', filters = {}, enabled = true } = options;

    // Fetch state-level data
    const stateQuery = useQuery({
        queryKey: ['map-data', 'state', metric, filters],
        queryFn: async (): Promise<StateMapData[]> => {
            try {
                // Try coverage endpoint first
                const response = await apiService.get('/coverage/by-state', {
                    params: { tier: filters.tier, min_coverage: filters.minCoverage },
                });

                // Transform API response to StateMapData
                if (response.data && Array.isArray(response.data.states)) {
                    return response.data.states.map((s: any) => ({
                        stateCode: s.state_code || s.state,
                        stateName: STATE_NAMES[s.state_code || s.state] || s.state_name,
                        value: metric === 'coverage' ? s.coverage_pct :
                            metric === 'records' ? s.total_records : s.recent_activity,
                        metadata: {
                            jurisdictions: s.total_jurisdictions || 0,
                            activeJurisdictions: s.active_jurisdictions || 0,
                            records: s.total_records || 0,
                            coverage: s.coverage_pct || 0,
                            lastUpdated: s.last_updated || null,
                            tier: s.tier || 4,
                        },
                    }));
                }
                throw new Error('Invalid response format');
            } catch (error) {
                // Fallback: derive from jurisdictions
                const response = await apiService.getJurisdictions();
                return processJurisdictionsToStateData(response.data, metric);
            }
        },
        enabled: enabled && level === 'state',
        staleTime: 5 * 60 * 1000,
        retry: 2,
    });

    // Fetch county-level data when a state is selected
    const countyQuery = useQuery({
        queryKey: ['map-data', 'county', filters.stateCode, metric],
        queryFn: async (): Promise<CountyMapData[]> => {
            if (!filters.stateCode) return [];

            try {
                const response = await apiService.get(`/coverage/by-state/${filters.stateCode}/counties`);

                if (response.data && Array.isArray(response.data.counties)) {
                    return response.data.counties.map((c: any) => ({
                        fips: c.fips,
                        name: c.name,
                        stateCode: filters.stateCode,
                        value: metric === 'coverage' ? c.coverage_pct :
                            metric === 'records' ? c.total_records : c.recent_activity,
                        metadata: {
                            records: c.total_records || 0,
                            coverage: c.coverage_pct || 0,
                            dataCategories: c.data_categories || [],
                        },
                    }));
                }
                return [];
            } catch (error) {
                console.warn('County data not available:', error);
                return [];
            }
        },
        enabled: enabled && level === 'county' && !!filters.stateCode,
        staleTime: 5 * 60 * 1000,
        retry: 1,
    });

    // Process jurisdictions to state-level map data
    const processJurisdictionsToStateData = useCallback(
        (jurisdictions: any[], metric: string): StateMapData[] => {
            const stateStats: Record<string, {
                total: number;
                active: number;
                records: number;
                lastUpdated: string | null;
            }> = {};

            jurisdictions.forEach((j: any) => {
                const state = j.state || 'Unknown';
                if (state === 'Unknown') return;

                if (!stateStats[state]) {
                    stateStats[state] = { total: 0, active: 0, records: 0, lastUpdated: null };
                }
                stateStats[state].total++;
                if (j.status === 'active' || j.is_active) {
                    stateStats[state].active++;
                }
                stateStats[state].records += j.record_count || 0;
                const currentLastUpdated = stateStats[state].lastUpdated;
                if (j.updated_at && (!currentLastUpdated || j.updated_at > currentLastUpdated)) {
                    stateStats[state].lastUpdated = j.updated_at;
                }
            });

            return Object.entries(stateStats)
                .filter(([code]) => code !== 'Unknown')
                .map(([code, stats]) => {
                    const coverage = stats.total > 0 ? Math.round((stats.active / stats.total) * 100) : 0;
                    return {
                        stateCode: code,
                        stateName: STATE_NAMES[code] || code,
                        value: metric === 'coverage' ? coverage :
                            metric === 'records' ? stats.records : stats.active,
                        metadata: {
                            jurisdictions: stats.total,
                            activeJurisdictions: stats.active,
                            records: stats.records,
                            coverage,
                            lastUpdated: stats.lastUpdated,
                            tier: getStateTier(code),
                        },
                    };
                });
        },
        []
    );

    // Get state tier based on population priority
    const getStateTier = (stateCode: string): number => {
        const tier1 = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI'];
        const tier2 = ['NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI', 'CO', 'MN', 'SC', 'AL', 'LA'];
        const tier3 = ['KY', 'OR', 'OK', 'CT', 'UT', 'IA', 'NV', 'AR', 'MS', 'KS', 'NM', 'NE', 'ID', 'WV', 'HI', 'NH', 'ME', 'MT', 'RI', 'DE', 'SD', 'ND', 'AK', 'DC', 'VT', 'WY'];

        if (tier1.includes(stateCode)) return 1;
        if (tier2.includes(stateCode)) return 2;
        if (tier3.includes(stateCode)) return 3;
        return 4;
    };

    // Computed statistics
    const stats = useMemo(() => {
        const data = level === 'state' ? stateQuery.data : countyQuery.data;
        if (!data || data.length === 0) {
            return { total: 0, avgCoverage: 0, totalRecords: 0, highCoverage: 0, lowCoverage: 0 };
        }

        const stateData = data as StateMapData[];
        const coverages = stateData.map((d) => d.metadata?.coverage || d.value);
        const avgCoverage = Math.round(coverages.reduce((a, b) => a + b, 0) / coverages.length);
        const totalRecords = stateData.reduce((acc, d) => acc + (d.metadata?.records || 0), 0);
        const highCoverage = stateData.filter((d) => (d.metadata?.coverage || d.value) >= 75).length;
        const lowCoverage = stateData.filter((d) => (d.metadata?.coverage || d.value) < 25).length;

        return {
            total: data.length,
            avgCoverage,
            totalRecords,
            highCoverage,
            lowCoverage,
        };
    }, [level, stateQuery.data, countyQuery.data]);

    return {
        // Data
        stateData: stateQuery.data || [],
        countyData: countyQuery.data || [],

        // Status
        isLoading: level === 'state' ? stateQuery.isLoading : countyQuery.isLoading,
        isError: level === 'state' ? stateQuery.isError : countyQuery.isError,
        error: level === 'state' ? stateQuery.error : countyQuery.error,

        // Helpers
        getStateByCode: (code: string) => stateQuery.data?.find((s) => s.stateCode === code),
        getStateName: (code: string) => STATE_NAMES[code] || code,

        // Statistics
        stats,

        // Refetch
        refetch: level === 'state' ? stateQuery.refetch : countyQuery.refetch,
    };
}

export default useMapData;
