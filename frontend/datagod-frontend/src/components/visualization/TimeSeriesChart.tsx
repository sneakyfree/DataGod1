/**
 * TimeSeriesChart Component
 * 
 * Advanced time series visualization with zoom, pan, annotations,
 * trend lines, and moving averages.
 */

'use client';

import React, { useState, useMemo, useCallback, useRef } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Brush,
    ReferenceLine,
    ReferenceArea,
    Area,
    ComposedChart,
} from 'recharts';

// Types
interface DataPoint {
    date: string | Date;
    [key: string]: any;
}

interface SeriesConfig {
    key: string;
    name: string;
    color: string;
    type?: 'line' | 'area' | 'bar';
    strokeWidth?: number;
    dot?: boolean;
    hidden?: boolean;
}

interface Annotation {
    id: string;
    date: string;
    label: string;
    color?: string;
    description?: string;
}

interface TrendLineConfig {
    show: boolean;
    color?: string;
    strokeDasharray?: string;
}

interface MovingAverageConfig {
    show: boolean;
    period: number;
    color?: string;
}

interface TimeSeriesChartProps {
    data: DataPoint[];
    series: SeriesConfig[];
    title?: string;
    subtitle?: string;
    height?: number;
    annotations?: Annotation[];
    showBrush?: boolean;
    showGrid?: boolean;
    showLegend?: boolean;
    trendLine?: TrendLineConfig;
    movingAverage?: MovingAverageConfig;
    dateFormat?: string;
    valueFormat?: (value: number) => string;
    onDataPointClick?: (point: DataPoint, seriesKey: string) => void;
    onRangeChange?: (start: string, end: string) => void;
    className?: string;
}

// Color palette
const DEFAULT_COLORS = [
    '#2563eb', // Blue
    '#16a34a', // Green
    '#dc2626', // Red
    '#9333ea', // Purple
    '#ea580c', // Orange
    '#0891b2', // Cyan
];

// Format date for display
const formatDate = (dateStr: string | Date, format: string = 'short'): string => {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;

    if (format === 'short') {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else if (format === 'long') {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    return date.toISOString().split('T')[0];
};

// Calculate moving average
const calculateMovingAverage = (data: DataPoint[], key: string, period: number): number[] => {
    const result: number[] = [];

    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            result.push(NaN);
        } else {
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j][key] || 0;
            }
            result.push(sum / period);
        }
    }

    return result;
};

// Calculate trend line (simple linear regression)
const calculateTrendLine = (data: DataPoint[], key: string): { slope: number; intercept: number } => {
    const n = data.length;
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumXX = 0;

    data.forEach((point, i) => {
        const y = point[key] || 0;
        sumX += i;
        sumY += y;
        sumXY += i * y;
        sumXX += i * i;
    });

    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    return { slope, intercept };
};

// Custom tooltip
const CustomTooltip = ({ active, payload, label, valueFormat }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
            <p className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                {formatDate(label, 'long')}
            </p>
            {payload.map((entry: any, index: number) => (
                <p key={index} className="text-sm" style={{ color: entry.color }}>
                    {entry.name}: {valueFormat ? valueFormat(entry.value) : entry.value?.toLocaleString()}
                </p>
            ))}
        </div>
    );
};

// Export button component
const ExportButton = ({ onExport }: { onExport: (format: 'png' | 'csv') => void }) => {
    const [open, setOpen] = useState(false);

    return (
        <div className="relative">
            <button
                onClick={() => setOpen(!open)}
                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md flex items-center gap-1"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export
            </button>

            {open && (
                <div className="absolute right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg py-1 z-10">
                    <button
                        onClick={() => { onExport('png'); setOpen(false); }}
                        className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                        Export as PNG
                    </button>
                    <button
                        onClick={() => { onExport('csv'); setOpen(false); }}
                        className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                        Export as CSV
                    </button>
                </div>
            )}
        </div>
    );
};

export function TimeSeriesChart({
    data,
    series,
    title,
    subtitle,
    height = 400,
    annotations = [],
    showBrush = true,
    showGrid = true,
    showLegend = true,
    trendLine = { show: false },
    movingAverage = { show: false, period: 7 },
    dateFormat = 'short',
    valueFormat,
    onDataPointClick,
    onRangeChange,
    className = '',
}: TimeSeriesChartProps) {
    const chartRef = useRef<HTMLDivElement>(null);
    const [hiddenSeries, setHiddenSeries] = useState<Set<string>>(new Set());
    const [zoomDomain, setZoomDomain] = useState<{ startIndex: number; endIndex: number } | null>(null);

    // Process data with moving average and trend
    const processedData = useMemo(() => {
        if (!data.length) return [];

        let result = data.map((point, index) => ({
            ...point,
            _index: index,
            _dateFormatted: formatDate(point.date, dateFormat),
        }));

        // Add moving averages
        if (movingAverage.show) {
            series.forEach(s => {
                if (!s.hidden) {
                    const ma = calculateMovingAverage(data, s.key, movingAverage.period);
                    result = result.map((point, i) => ({
                        ...point,
                        [`${s.key}_ma`]: ma[i],
                    }));
                }
            });
        }

        // Add trend lines
        if (trendLine.show) {
            series.forEach(s => {
                if (!s.hidden) {
                    const { slope, intercept } = calculateTrendLine(data, s.key);
                    result = result.map((point, i) => ({
                        ...point,
                        [`${s.key}_trend`]: slope * i + intercept,
                    }));
                }
            });
        }

        return result;
    }, [data, series, movingAverage, trendLine, dateFormat]);

    // Handle legend click to toggle series
    const handleLegendClick = useCallback((dataKey: string) => {
        setHiddenSeries(prev => {
            const next = new Set(prev);
            if (next.has(dataKey)) {
                next.delete(dataKey);
            } else {
                next.add(dataKey);
            }
            return next;
        });
    }, []);

    // Handle brush change
    const handleBrushChange = useCallback((domain: any) => {
        if (domain && domain.startIndex !== undefined) {
            setZoomDomain({ startIndex: domain.startIndex, endIndex: domain.endIndex });

            if (onRangeChange && processedData.length) {
                const start = processedData[domain.startIndex]?.date;
                const end = processedData[domain.endIndex]?.date;
                if (start && end) {
                    onRangeChange(String(start), String(end));
                }
            }
        }
    }, [onRangeChange, processedData]);

    // Export functions
    const handleExport = useCallback((format: 'png' | 'csv') => {
        if (format === 'csv') {
            // Generate CSV
            const headers = ['date', ...series.map(s => s.key)];
            const rows = data.map(point =>
                [point.date, ...series.map(s => point[s.key] ?? '')].join(',')
            );
            const csv = [headers.join(','), ...rows].join('\n');

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chart-data-${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } else if (format === 'png') {
            // Export PNG using canvas
            if (chartRef.current) {
                const svgElement = chartRef.current.querySelector('svg');
                if (svgElement) {
                    const svgData = new XMLSerializer().serializeToString(svgElement);
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    const img = new Image();

                    canvas.width = svgElement.clientWidth * 2;
                    canvas.height = svgElement.clientHeight * 2;

                    img.onload = () => {
                        if (ctx) {
                            ctx.fillStyle = 'white';
                            ctx.fillRect(0, 0, canvas.width, canvas.height);
                            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                            const pngUrl = canvas.toDataURL('image/png');
                            const a = document.createElement('a');
                            a.href = pngUrl;
                            a.download = `chart-${new Date().toISOString().split('T')[0]}.png`;
                            a.click();
                        }
                    };

                    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
                }
            }
        }
    }, [data, series]);

    // Calculate y-axis domain
    const yDomain = useMemo(() => {
        const values: number[] = [];

        processedData.forEach((point: Record<string, any>) => {
            series.forEach(s => {
                if (!hiddenSeries.has(s.key)) {
                    const val = point[s.key];
                    if (typeof val === 'number' && !isNaN(val)) {
                        values.push(val);
                    }
                }
            });
        });

        if (!values.length) return [0, 100];

        const min = Math.min(...values);
        const max = Math.max(...values);
        const padding = (max - min) * 0.1;

        return [Math.floor(min - padding), Math.ceil(max + padding)];
    }, [processedData, series, hiddenSeries]);

    if (!data.length) {
        return (
            <div className={`flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-900 rounded-lg ${className}`}>
                <p className="text-gray-500 dark:text-gray-400">No data available</p>
            </div>
        );
    }

    return (
        <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm ${className}`} ref={chartRef}>
            {/* Header */}
            {(title || subtitle) && (
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div>
                        {title && <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>}
                        {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
                    </div>
                    <ExportButton onExport={handleExport} />
                </div>
            )}

            {/* Chart */}
            <div className="p-4">
                <ResponsiveContainer width="100%" height={height}>
                    <ComposedChart
                        data={processedData}
                        margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                    >
                        {showGrid && (
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="#e5e7eb"
                                className="dark:stroke-gray-700"
                            />
                        )}

                        <XAxis
                            dataKey="_dateFormatted"
                            tick={{ fontSize: 12, fill: '#6b7280' }}
                            tickLine={{ stroke: '#d1d5db' }}
                            axisLine={{ stroke: '#d1d5db' }}
                        />

                        <YAxis
                            domain={yDomain}
                            tick={{ fontSize: 12, fill: '#6b7280' }}
                            tickLine={{ stroke: '#d1d5db' }}
                            axisLine={{ stroke: '#d1d5db' }}
                            tickFormatter={valueFormat}
                        />

                        <Tooltip content={<CustomTooltip valueFormat={valueFormat} />} />

                        {showLegend && (
                            <Legend
                                onClick={(e) => handleLegendClick(e.dataKey as string)}
                                wrapperStyle={{ cursor: 'pointer' }}
                            />
                        )}

                        {/* Annotations */}
                        {annotations.map(annotation => (
                            <ReferenceLine
                                key={annotation.id}
                                x={formatDate(annotation.date, dateFormat)}
                                stroke={annotation.color || '#f59e0b'}
                                strokeDasharray="3 3"
                                label={{
                                    value: annotation.label,
                                    position: 'top',
                                    fill: annotation.color || '#f59e0b',
                                    fontSize: 12,
                                }}
                            />
                        ))}

                        {/* Main series lines */}
                        {series.map((s, index) => {
                            const color = s.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length];
                            const isHidden = hiddenSeries.has(s.key);

                            if (s.type === 'area') {
                                return (
                                    <Area
                                        key={s.key}
                                        type="monotone"
                                        dataKey={s.key}
                                        name={s.name}
                                        stroke={color}
                                        fill={color}
                                        fillOpacity={0.2}
                                        strokeWidth={s.strokeWidth || 2}
                                        dot={s.dot !== false}
                                        hide={isHidden}
                                    />
                                );
                            }

                            return (
                                <Line
                                    key={s.key}
                                    type="monotone"
                                    dataKey={s.key}
                                    name={s.name}
                                    stroke={color}
                                    strokeWidth={s.strokeWidth || 2}
                                    dot={s.dot !== false ? { r: 3, strokeWidth: 2 } : false}
                                    activeDot={{ r: 5, strokeWidth: 2 }}
                                    hide={isHidden}
                                />
                            );
                        })}

                        {/* Moving average lines */}
                        {movingAverage.show && series.map((s, index) => {
                            const color = movingAverage.color || '#9ca3af';
                            return (
                                <Line
                                    key={`${s.key}_ma`}
                                    type="monotone"
                                    dataKey={`${s.key}_ma`}
                                    name={`${s.name} (${movingAverage.period}-day MA)`}
                                    stroke={color}
                                    strokeWidth={1.5}
                                    strokeDasharray="4 2"
                                    dot={false}
                                    hide={hiddenSeries.has(s.key)}
                                />
                            );
                        })}

                        {/* Trend lines */}
                        {trendLine.show && series.map((s, index) => {
                            const color = trendLine.color || '#ef4444';
                            return (
                                <Line
                                    key={`${s.key}_trend`}
                                    type="monotone"
                                    dataKey={`${s.key}_trend`}
                                    name={`${s.name} (Trend)`}
                                    stroke={color}
                                    strokeWidth={1.5}
                                    strokeDasharray={trendLine.strokeDasharray || '6 3'}
                                    dot={false}
                                    hide={hiddenSeries.has(s.key)}
                                />
                            );
                        })}

                        {/* Brush for zoom/pan */}
                        {showBrush && (
                            <Brush
                                dataKey="_dateFormatted"
                                height={30}
                                stroke="#8884d8"
                                fill="#f3f4f6"
                                onChange={handleBrushChange}
                            />
                        )}
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            {/* Stats footer */}
            <div className="px-4 pb-4 flex gap-6 text-sm text-gray-500 dark:text-gray-400">
                <span>Data points: {data.length}</span>
                <span>Date range: {formatDate(data[0]?.date, 'long')} - {formatDate(data[data.length - 1]?.date, 'long')}</span>
            </div>
        </div>
    );
}

export default TimeSeriesChart;
