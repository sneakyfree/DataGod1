'use client';

import React, { useState, useMemo, useCallback } from 'react';
import {
    ComposableMap,
    Geographies,
    Geography,
    ZoomableGroup,
} from 'react-simple-maps';
import { scaleQuantile } from 'd3-scale';
import {
    Box,
    Paper,
    Typography,
    Tooltip,
    CircularProgress,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Slider,
    IconButton,
    Stack,
    Chip,
    useTheme,
} from '@mui/material';
import {
    ZoomIn as ZoomInIcon,
    ZoomOut as ZoomOutIcon,
    CenterFocusStrong as CenterIcon,
    Download as DownloadIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// US TopoJSON - using CDN for reliability
const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json';

// State FIPS to abbreviation mapping
const STATE_FIPS_TO_ABBR: Record<string, string> = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA',
    '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL',
    '13': 'GA', '15': 'HI', '16': 'ID', '17': 'IL', '18': 'IN',
    '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME',
    '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS',
    '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH',
    '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND',
    '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI',
    '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT',
    '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI',
    '56': 'WY', '72': 'PR',
};

// State names
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

// Color schemes for different metrics
const COLOR_SCHEMES = {
    coverage: ['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15'],
    records: ['#edf8e9', '#bae4b3', '#74c476', '#31a354', '#006d2c'],
    activity: ['#eff3ff', '#bdd7e7', '#6baed6', '#3182bd', '#08519c'],
};

export interface HeatMapData {
    stateCode: string;
    value: number;
    metadata?: {
        jurisdictions?: number;
        records?: number;
        lastUpdated?: string;
        coverage?: number;
    };
}

export interface HeatMapProps {
    data?: HeatMapData[];
    metric?: 'coverage' | 'records' | 'activity';
    title?: string;
    onStateClick?: (stateCode: string, data: HeatMapData | null) => void;
    height?: number;
    showLegend?: boolean;
    showControls?: boolean;
}

export const HeatMap: React.FC<HeatMapProps> = ({
    data: externalData,
    metric = 'coverage',
    title = 'Jurisdiction Coverage by State',
    onStateClick,
    height = 500,
    showLegend = true,
    showControls = true,
}) => {
    const theme = useTheme();
    const [position, setPosition] = useState({ coordinates: [-96, 38] as [number, number], zoom: 1 });
    const [tooltipContent, setTooltipContent] = useState<string>('');
    const [selectedState, setSelectedState] = useState<string | null>(null);
    const [currentMetric, setCurrentMetric] = useState(metric);

    // Fetch coverage data from API if not provided
    const { data: apiData, isLoading, error } = useQuery({
        queryKey: ['coverage-by-state'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/coverage/by-state');
                return response.data;
            } catch (err) {
                // Fallback to jurisdictions endpoint
                const response = await apiService.getJurisdictions();
                return processJurisdictionsToHeatMap(response.data);
            }
        },
        enabled: !externalData,
        staleTime: 5 * 60 * 1000,
        retry: 2,
    });

    // Process jurisdictions data to heatmap format
    const processJurisdictionsToHeatMap = useCallback((jurisdictions: any[]): HeatMapData[] => {
        const stateStats: Record<string, { total: number; active: number; records: number }> = {};

        jurisdictions.forEach((j: any) => {
            const state = j.state || 'Unknown';
            if (!stateStats[state]) {
                stateStats[state] = { total: 0, active: 0, records: 0 };
            }
            stateStats[state].total++;
            if (j.status === 'active' || j.is_active) {
                stateStats[state].active++;
            }
            stateStats[state].records += j.record_count || 0;
        });

        return Object.entries(stateStats).map(([stateCode, stats]) => ({
            stateCode,
            value: Math.round((stats.active / stats.total) * 100),
            metadata: {
                jurisdictions: stats.total,
                records: stats.records,
                coverage: Math.round((stats.active / stats.total) * 100),
            },
        }));
    }, []);

    // Use external data or API data
    const heatMapData = useMemo(() => {
        return externalData || apiData || [];
    }, [externalData, apiData]);

    // Create data map for quick lookup
    const dataMap = useMemo(() => {
        const map = new Map<string, HeatMapData>();
        heatMapData.forEach((d: HeatMapData) => map.set(d.stateCode, d));
        return map;
    }, [heatMapData]);

    // Create color scale
    const colorScale = useMemo(() => {
        const values = heatMapData.map((d: HeatMapData) => d.value);
        const colors = COLOR_SCHEMES[currentMetric];
        return scaleQuantile<string>()
            .domain(values.length > 0 ? values : [0, 25, 50, 75, 100])
            .range(colors);
    }, [heatMapData, currentMetric]);

    // Handle zoom
    const handleZoomIn = () => {
        if (position.zoom >= 8) return;
        setPosition((pos) => ({ ...pos, zoom: pos.zoom * 1.5 }));
    };

    const handleZoomOut = () => {
        if (position.zoom <= 1) return;
        setPosition((pos) => ({ ...pos, zoom: pos.zoom / 1.5 }));
    };

    const handleCenter = () => {
        setPosition({ coordinates: [-96, 38], zoom: 1 });
    };

    const handleMoveEnd = (position: { coordinates: [number, number]; zoom: number }) => {
        setPosition(position);
    };

    // Handle state click
    const handleStateClick = (stateCode: string) => {
        setSelectedState(stateCode === selectedState ? null : stateCode);
        if (onStateClick) {
            onStateClick(stateCode, dataMap.get(stateCode) || null);
        }
    };

    // Export map as SVG
    const handleExport = () => {
        const svg = document.querySelector('#heatmap-svg');
        if (svg) {
            const svgData = new XMLSerializer().serializeToString(svg);
            const blob = new Blob([svgData], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `coverage-map-${new Date().toISOString().split('T')[0]}.svg`;
            link.click();
            URL.revokeObjectURL(url);
        }
    };

    if (isLoading) {
        return (
            <Paper sx={{ p: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
                <CircularProgress />
                <Typography sx={{ ml: 2 }}>Loading coverage data...</Typography>
            </Paper>
        );
    }

    if (error) {
        return (
            <Paper sx={{ p: 4, height }}>
                <Typography color="error">Failed to load coverage data. Please try again.</Typography>
            </Paper>
        );
    }

    return (
        <Paper sx={{ p: 2, height: 'auto' }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">{title}</Typography>
                {showControls && (
                    <Stack direction="row" spacing={1} alignItems="center">
                        <FormControl size="small" sx={{ minWidth: 120 }}>
                            <InputLabel>Metric</InputLabel>
                            <Select
                                value={currentMetric}
                                label="Metric"
                                onChange={(e) => setCurrentMetric(e.target.value as typeof currentMetric)}
                            >
                                <MenuItem value="coverage">Coverage %</MenuItem>
                                <MenuItem value="records">Record Count</MenuItem>
                                <MenuItem value="activity">Recent Activity</MenuItem>
                            </Select>
                        </FormControl>
                        <IconButton size="small" onClick={handleZoomIn} title="Zoom In">
                            <ZoomInIcon />
                        </IconButton>
                        <IconButton size="small" onClick={handleZoomOut} title="Zoom Out">
                            <ZoomOutIcon />
                        </IconButton>
                        <IconButton size="small" onClick={handleCenter} title="Reset View">
                            <CenterIcon />
                        </IconButton>
                        <IconButton size="small" onClick={handleExport} title="Export SVG">
                            <DownloadIcon />
                        </IconButton>
                    </Stack>
                )}
            </Box>

            {/* Map Container */}
            <Box sx={{ position: 'relative' }}>
                <ComposableMap
                    projection="geoAlbersUsa"
                    projectionConfig={{ scale: 1000 }}
                    style={{ width: '100%', height }}
                >
                    <ZoomableGroup
                        zoom={position.zoom}
                        center={position.coordinates}
                        onMoveEnd={() => { }}
                    >
                        <Geographies geography={GEO_URL}>
                            {({ geographies }) =>
                                geographies.map((geo) => {
                                    const stateCode = STATE_FIPS_TO_ABBR[geo.id] || '';
                                    const stateData = dataMap.get(stateCode);
                                    const value = stateData?.value || 0;
                                    const isSelected = selectedState === stateCode;

                                    return (
                                        <Tooltip
                                            key={geo.rsmKey}
                                            title={
                                                <Box>
                                                    <Typography variant="subtitle2">
                                                        {STATE_NAMES[stateCode] || stateCode}
                                                    </Typography>
                                                    {stateData ? (
                                                        <>
                                                            <Typography variant="body2">
                                                                Coverage: {stateData.metadata?.coverage ?? value}%
                                                            </Typography>
                                                            <Typography variant="body2">
                                                                Jurisdictions: {stateData.metadata?.jurisdictions ?? 'N/A'}
                                                            </Typography>
                                                            <Typography variant="body2">
                                                                Records: {stateData.metadata?.records?.toLocaleString() ?? 'N/A'}
                                                            </Typography>
                                                        </>
                                                    ) : (
                                                        <Typography variant="body2">No data available</Typography>
                                                    )}
                                                </Box>
                                            }
                                            arrow
                                            placement="top"
                                        >
                                            <Geography
                                                geography={geo}
                                                onClick={() => handleStateClick(stateCode)}
                                                style={{
                                                    default: {
                                                        fill: stateData ? colorScale(value) : '#EEE',
                                                        stroke: isSelected ? theme.palette.primary.main : '#FFF',
                                                        strokeWidth: isSelected ? 2 : 0.5,
                                                        outline: 'none',
                                                        cursor: 'pointer',
                                                    },
                                                    hover: {
                                                        fill: stateData ? colorScale(value) : '#DDD',
                                                        stroke: theme.palette.primary.main,
                                                        strokeWidth: 1.5,
                                                        outline: 'none',
                                                        cursor: 'pointer',
                                                    },
                                                    pressed: {
                                                        fill: theme.palette.primary.light,
                                                        stroke: theme.palette.primary.main,
                                                        strokeWidth: 2,
                                                        outline: 'none',
                                                    },
                                                }}
                                            />
                                        </Tooltip>
                                    );
                                })
                            }
                        </Geographies>
                    </ZoomableGroup>
                </ComposableMap>

                {/* Selected State Info */}
                {selectedState && dataMap.get(selectedState) && (
                    <Paper
                        elevation={3}
                        sx={{
                            position: 'absolute',
                            bottom: 16,
                            left: 16,
                            p: 2,
                            minWidth: 200,
                            backgroundColor: 'rgba(255,255,255,0.95)',
                        }}
                    >
                        <Typography variant="subtitle1" fontWeight="bold">
                            {STATE_NAMES[selectedState]}
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                            <Chip
                                label={`${dataMap.get(selectedState)?.metadata?.coverage ?? 0}% Coverage`}
                                color="primary"
                                size="small"
                            />
                            <Chip
                                label={`${dataMap.get(selectedState)?.metadata?.jurisdictions ?? 0} Jurisdictions`}
                                size="small"
                            />
                        </Stack>
                    </Paper>
                )}
            </Box>

            {/* Legend */}
            {showLegend && (
                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption">Low</Typography>
                    {COLOR_SCHEMES[currentMetric].map((color, i) => (
                        <Box
                            key={i}
                            sx={{
                                width: 40,
                                height: 16,
                                backgroundColor: color,
                                border: '1px solid #ccc',
                            }}
                        />
                    ))}
                    <Typography variant="caption">High</Typography>
                </Box>
            )}

            {/* Stats Summary */}
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 4 }}>
                <Box textAlign="center">
                    <Typography variant="h5" color="primary">
                        {heatMapData.length}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        States with Data
                    </Typography>
                </Box>
                <Box textAlign="center">
                    <Typography variant="h5" color="primary">
                        {Math.round(heatMapData.reduce((acc: number, d: HeatMapData) => acc + d.value, 0) / (heatMapData.length || 1))}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        Avg Coverage
                    </Typography>
                </Box>
                <Box textAlign="center">
                    <Typography variant="h5" color="primary">
                        {heatMapData.reduce((acc: number, d: HeatMapData) => acc + (d.metadata?.records || 0), 0).toLocaleString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        Total Records
                    </Typography>
                </Box>
            </Box>
        </Paper>
    );
};

export default HeatMap;
