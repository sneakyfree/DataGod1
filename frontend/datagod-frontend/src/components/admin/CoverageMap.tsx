'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  CircularProgress,
} from '@mui/material';

interface StateCoverage {
  state: string;
  name: string;
  total_jurisdictions: number;
  covered_count: number;
  coverage_percentage: number;
  population: number;
}

interface CoverageMapProps {
  data?: StateCoverage[];
  loading?: boolean;
  onStateClick?: (state: string) => void;
}

// US State coordinates for a simple grid-based map
const STATE_POSITIONS: Record<string, { row: number; col: number }> = {
  AK: { row: 0, col: 0 },
  ME: { row: 0, col: 10 },
  VT: { row: 1, col: 9 },
  NH: { row: 1, col: 10 },
  WA: { row: 1, col: 1 },
  MT: { row: 1, col: 2 },
  ND: { row: 1, col: 3 },
  MN: { row: 1, col: 4 },
  WI: { row: 1, col: 5 },
  MI: { row: 1, col: 6 },
  NY: { row: 2, col: 8 },
  MA: { row: 2, col: 9 },
  RI: { row: 2, col: 10 },
  OR: { row: 2, col: 1 },
  ID: { row: 2, col: 2 },
  WY: { row: 2, col: 3 },
  SD: { row: 2, col: 4 },
  IA: { row: 2, col: 5 },
  IL: { row: 2, col: 6 },
  IN: { row: 2, col: 7 },
  CT: { row: 3, col: 9 },
  NJ: { row: 3, col: 10 },
  NV: { row: 3, col: 1 },
  UT: { row: 3, col: 2 },
  CO: { row: 3, col: 3 },
  NE: { row: 3, col: 4 },
  MO: { row: 3, col: 5 },
  KY: { row: 3, col: 6 },
  OH: { row: 3, col: 7 },
  PA: { row: 3, col: 8 },
  DE: { row: 4, col: 9 },
  MD: { row: 4, col: 10 },
  CA: { row: 4, col: 1 },
  AZ: { row: 4, col: 2 },
  NM: { row: 4, col: 3 },
  KS: { row: 4, col: 4 },
  AR: { row: 4, col: 5 },
  TN: { row: 4, col: 6 },
  WV: { row: 4, col: 7 },
  VA: { row: 4, col: 8 },
  DC: { row: 5, col: 9 },
  NC: { row: 5, col: 8 },
  OK: { row: 5, col: 4 },
  LA: { row: 5, col: 5 },
  MS: { row: 5, col: 6 },
  AL: { row: 5, col: 7 },
  TX: { row: 6, col: 3 },
  GA: { row: 6, col: 7 },
  SC: { row: 6, col: 8 },
  HI: { row: 7, col: 1 },
  FL: { row: 7, col: 8 },
  // Territories
  PR: { row: 7, col: 10 },
  VI: { row: 8, col: 10 },
  GU: { row: 8, col: 0 },
  AS: { row: 8, col: 1 },
  MP: { row: 8, col: 2 },
};

const STATE_NAMES: Record<string, string> = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
  CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', DC: 'District of Columbia',
  FL: 'Florida', GA: 'Georgia', HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois',
  IN: 'Indiana', IA: 'Iowa', KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana',
  ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota',
  MS: 'Mississippi', MO: 'Missouri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada',
  NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico', NY: 'New York',
  NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma', OR: 'Oregon',
  PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina', SD: 'South Dakota',
  TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont', VA: 'Virginia',
  WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming',
  PR: 'Puerto Rico', GU: 'Guam', VI: 'Virgin Islands', AS: 'American Samoa',
  MP: 'Northern Mariana Islands',
};

export function CoverageMap({ data = [], loading = false, onStateClick }: CoverageMapProps) {
  const [colorMode, setColorMode] = useState<'coverage' | 'population' | 'jurisdictions'>('coverage');

  const getColor = (state: string): string => {
    const stateData = data.find(d => d.state === state);
    if (!stateData) return '#e0e0e0';

    if (colorMode === 'coverage') {
      const pct = stateData.coverage_percentage;
      if (pct >= 90) return '#2e7d32'; // Dark green
      if (pct >= 70) return '#4caf50'; // Green
      if (pct >= 50) return '#8bc34a'; // Light green
      if (pct >= 30) return '#ffc107'; // Amber
      if (pct >= 10) return '#ff9800'; // Orange
      return '#f44336'; // Red
    }

    if (colorMode === 'population') {
      const pop = stateData.population;
      if (pop >= 30000000) return '#1565c0';
      if (pop >= 15000000) return '#1976d2';
      if (pop >= 5000000) return '#2196f3';
      if (pop >= 2000000) return '#64b5f6';
      if (pop >= 500000) return '#90caf9';
      return '#bbdefb';
    }

    if (colorMode === 'jurisdictions') {
      const count = stateData.total_jurisdictions;
      if (count >= 200) return '#7b1fa2';
      if (count >= 100) return '#9c27b0';
      if (count >= 50) return '#ba68c8';
      if (count >= 25) return '#ce93d8';
      if (count >= 10) return '#e1bee7';
      return '#f3e5f5';
    }

    return '#e0e0e0';
  };

  const getTooltipContent = (state: string): string => {
    const stateData = data.find(d => d.state === state);
    if (!stateData) return `${STATE_NAMES[state] || state}: No data`;

    return `${STATE_NAMES[state]} (${state})
Coverage: ${stateData.coverage_percentage.toFixed(1)}%
Jurisdictions: ${stateData.total_jurisdictions}
Covered: ${stateData.covered_count}
Population: ${stateData.population.toLocaleString()}`;
  };

  const rows = Array.from({ length: 9 }, (_, i) => i);
  const cols = Array.from({ length: 11 }, (_, i) => i);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Coverage Map</Typography>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Color By</InputLabel>
          <Select
            value={colorMode}
            label="Color By"
            onChange={(e) => setColorMode(e.target.value as any)}
          >
            <MenuItem value="coverage">Coverage %</MenuItem>
            <MenuItem value="population">Population</MenuItem>
            <MenuItem value="jurisdictions">Jurisdictions</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(11, 1fr)',
          gridTemplateRows: 'repeat(9, 1fr)',
          gap: 0.5,
          maxWidth: 600,
          mx: 'auto',
        }}
      >
        {rows.map((row) =>
          cols.map((col) => {
            const state = Object.entries(STATE_POSITIONS).find(
              ([_, pos]) => pos.row === row && pos.col === col
            )?.[0];

            if (!state) {
              return <Box key={`${row}-${col}`} sx={{ aspectRatio: '1', minHeight: 30 }} />;
            }

            return (
              <Tooltip key={state} title={<pre style={{ margin: 0 }}>{getTooltipContent(state)}</pre>}>
                <Box
                  onClick={() => onStateClick?.(state)}
                  sx={{
                    aspectRatio: '1',
                    minHeight: 30,
                    backgroundColor: getColor(state),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: onStateClick ? 'pointer' : 'default',
                    border: '1px solid #fff',
                    borderRadius: 0.5,
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    '&:hover': {
                      transform: 'scale(1.1)',
                      boxShadow: 2,
                      zIndex: 1,
                    },
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 'bold',
                      color: '#fff',
                      textShadow: '1px 1px 1px rgba(0,0,0,0.3)',
                      fontSize: '0.65rem',
                    }}
                  >
                    {state}
                  </Typography>
                </Box>
              </Tooltip>
            );
          })
        )}
      </Box>

      {/* Legend */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 1, flexWrap: 'wrap' }}>
        {colorMode === 'coverage' && (
          <>
            <Chip label="90%+" size="small" sx={{ bgcolor: '#2e7d32', color: '#fff' }} />
            <Chip label="70-89%" size="small" sx={{ bgcolor: '#4caf50', color: '#fff' }} />
            <Chip label="50-69%" size="small" sx={{ bgcolor: '#8bc34a', color: '#fff' }} />
            <Chip label="30-49%" size="small" sx={{ bgcolor: '#ffc107', color: '#000' }} />
            <Chip label="10-29%" size="small" sx={{ bgcolor: '#ff9800', color: '#fff' }} />
            <Chip label="<10%" size="small" sx={{ bgcolor: '#f44336', color: '#fff' }} />
          </>
        )}
        {colorMode === 'population' && (
          <>
            <Chip label="30M+" size="small" sx={{ bgcolor: '#1565c0', color: '#fff' }} />
            <Chip label="15-30M" size="small" sx={{ bgcolor: '#1976d2', color: '#fff' }} />
            <Chip label="5-15M" size="small" sx={{ bgcolor: '#2196f3', color: '#fff' }} />
            <Chip label="2-5M" size="small" sx={{ bgcolor: '#64b5f6', color: '#fff' }} />
            <Chip label="<2M" size="small" sx={{ bgcolor: '#90caf9', color: '#000' }} />
          </>
        )}
        {colorMode === 'jurisdictions' && (
          <>
            <Chip label="200+" size="small" sx={{ bgcolor: '#7b1fa2', color: '#fff' }} />
            <Chip label="100-199" size="small" sx={{ bgcolor: '#9c27b0', color: '#fff' }} />
            <Chip label="50-99" size="small" sx={{ bgcolor: '#ba68c8', color: '#fff' }} />
            <Chip label="25-49" size="small" sx={{ bgcolor: '#ce93d8', color: '#fff' }} />
            <Chip label="<25" size="small" sx={{ bgcolor: '#e1bee7', color: '#000' }} />
          </>
        )}
      </Box>
    </Paper>
  );
}

export default CoverageMap;
