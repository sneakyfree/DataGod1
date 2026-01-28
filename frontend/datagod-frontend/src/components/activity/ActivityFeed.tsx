/**
 * ActivityFeed Component
 * 
 * Real-time activity tracking with filtering, aggregation,
 * search, and CSV export.
 */

'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';

// Types
interface Activity {
    id: string;
    type: 'login' | 'view' | 'create' | 'update' | 'delete' | 'export' | 'search' | 'share' | 'api_call';
    action: string;
    description: string;
    userId: string;
    userName?: string;
    targetType?: string;
    targetId?: string;
    targetName?: string;
    metadata?: Record<string, any>;
    ipAddress?: string;
    userAgent?: string;
    createdAt: string;
}

interface ActivityFilters {
    search: string;
    types: string[];
    dateFrom?: string;
    dateTo?: string;
    userId?: string;
}

interface AggregatedActivity {
    date: string;
    count: number;
    byType: Record<string, number>;
}

interface ActivityFeedProps {
    userId?: string;
    targetType?: string;
    targetId?: string;
    showFilters?: boolean;
    showExport?: boolean;
    limit?: number;
    realTime?: boolean;
    className?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

const ACTIVITY_TYPES = [
    { value: 'login', label: 'Login', icon: '🔐', color: 'bg-blue-100 text-blue-800' },
    { value: 'view', label: 'View', icon: '👁️', color: 'bg-gray-100 text-gray-800' },
    { value: 'create', label: 'Create', icon: '➕', color: 'bg-green-100 text-green-800' },
    { value: 'update', label: 'Update', icon: '✏️', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'delete', label: 'Delete', icon: '🗑️', color: 'bg-red-100 text-red-800' },
    { value: 'export', label: 'Export', icon: '📤', color: 'bg-purple-100 text-purple-800' },
    { value: 'search', label: 'Search', icon: '🔍', color: 'bg-indigo-100 text-indigo-800' },
    { value: 'share', label: 'Share', icon: '🔗', color: 'bg-cyan-100 text-cyan-800' },
    { value: 'api_call', label: 'API Call', icon: '⚡', color: 'bg-orange-100 text-orange-800' },
];

// Format time ago
const formatTimeAgo = (dateStr: string): string => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSeconds < 60) return 'just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const formatDateTime = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
};

// Activity type badge
const ActivityTypeBadge = ({ type }: { type: string }) => {
    const config = ACTIVITY_TYPES.find(t => t.value === type) || ACTIVITY_TYPES[0];
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${config.color}`}>
            <span>{config.icon}</span>
            {config.label}
        </span>
    );
};

// Single activity item
const ActivityItem = ({
    activity,
    expanded,
    onToggle
}: {
    activity: Activity;
    expanded: boolean;
    onToggle: () => void;
}) => (
    <div
        className={`p-3 border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer ${expanded ? 'bg-gray-50 dark:bg-gray-700/50' : ''
            }`}
        onClick={onToggle}
    >
        <div className="flex items-start gap-3">
            <ActivityTypeBadge type={activity.type} />

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{activity.userName || 'Unknown User'}</span>
                    <span className="text-xs text-gray-500">{formatTimeAgo(activity.createdAt)}</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 truncate">
                    {activity.description}
                </p>

                {expanded && (
                    <div className="mt-3 p-3 bg-gray-100 dark:bg-gray-800 rounded text-xs space-y-1">
                        <div><strong>Time:</strong> {formatDateTime(activity.createdAt)}</div>
                        <div><strong>Action:</strong> {activity.action}</div>
                        {activity.targetType && (
                            <div><strong>Target:</strong> {activity.targetType} / {activity.targetId}</div>
                        )}
                        {activity.ipAddress && <div><strong>IP:</strong> {activity.ipAddress}</div>}
                        {activity.metadata && (
                            <div><strong>Details:</strong> {JSON.stringify(activity.metadata)}</div>
                        )}
                    </div>
                )}
            </div>
        </div>
    </div>
);

// Aggregation chart
const AggregationChart = ({ data }: { data: AggregatedActivity[] }) => {
    if (!data.length) return null;

    const maxCount = Math.max(...data.map(d => d.count));

    return (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg mb-4">
            <h4 className="text-sm font-medium mb-3">Activity Over Time</h4>
            <div className="flex items-end gap-1 h-20">
                {data.map((d, i) => (
                    <div
                        key={i}
                        className="flex-1 bg-blue-500 hover:bg-blue-600 rounded-t cursor-pointer relative group"
                        style={{ height: `${maxCount > 0 ? (d.count / maxCount) * 100 : 0}%`, minHeight: d.count > 0 ? '4px' : '0' }}
                    >
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1 hidden group-hover:block bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                            {d.date}: {d.count} activities
                        </div>
                    </div>
                ))}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{data[0]?.date}</span>
                <span>{data[data.length - 1]?.date}</span>
            </div>
        </div>
    );
};

export function ActivityFeed({
    userId,
    targetType,
    targetId,
    showFilters = true,
    showExport = true,
    limit = 50,
    realTime = true,
    className = '',
}: ActivityFeedProps) {
    // State
    const [activities, setActivities] = useState<Activity[]>([]);
    const [aggregation, setAggregation] = useState<AggregatedActivity[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [showAggregation, setShowAggregation] = useState(false);

    // Filters
    const [filters, setFilters] = useState<ActivityFilters>({
        search: '',
        types: [],
        dateFrom: '',
        dateTo: '',
    });

    // Pagination
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);

    // Fetch activities
    const fetchActivities = useCallback(async (append = false) => {
        setLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams({
                page: String(append ? page : 1),
                limit: String(limit),
            });

            if (userId) params.set('userId', userId);
            if (targetType) params.set('targetType', targetType);
            if (targetId) params.set('targetId', targetId);
            if (filters.types.length) params.set('types', filters.types.join(','));
            if (filters.dateFrom) params.set('dateFrom', filters.dateFrom);
            if (filters.dateTo) params.set('dateTo', filters.dateTo);
            if (filters.search) params.set('search', filters.search);

            const response = await fetch(`${API_BASE_URL}/activities?${params}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                },
            });

            if (!response.ok) throw new Error('Failed to fetch activities');

            const data = await response.json();

            if (append) {
                setActivities(prev => [...prev, ...(data.activities || data)]);
            } else {
                setActivities(data.activities || data);
            }

            setHasMore((data.activities || data).length === limit);

            if (data.aggregation) {
                setAggregation(data.aggregation);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load activities');
        } finally {
            setLoading(false);
        }
    }, [userId, targetType, targetId, filters, page, limit]);

    useEffect(() => {
        fetchActivities();
    }, [fetchActivities]);

    // Real-time updates via polling (could be replaced with WebSocket)
    useEffect(() => {
        if (!realTime) return;

        const interval = setInterval(() => {
            fetchActivities();
        }, 30000); // Poll every 30 seconds

        return () => clearInterval(interval);
    }, [realTime, fetchActivities]);

    // Filter activities locally
    const filteredActivities = useMemo(() => {
        let result = [...activities];

        if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            result = result.filter(a =>
                a.description.toLowerCase().includes(searchLower) ||
                a.userName?.toLowerCase().includes(searchLower) ||
                a.action.toLowerCase().includes(searchLower)
            );
        }

        return result;
    }, [activities, filters.search]);

    // Export to CSV
    const handleExport = useCallback(() => {
        const headers = ['Time', 'Type', 'User', 'Action', 'Description', 'Target', 'IP Address'];
        const rows = filteredActivities.map(a => [
            formatDateTime(a.createdAt),
            a.type,
            a.userName || a.userId,
            a.action,
            a.description,
            a.targetType ? `${a.targetType}/${a.targetId}` : '',
            a.ipAddress || '',
        ]);

        const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `activity-log-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }, [filteredActivities]);

    // Toggle type filter
    const toggleTypeFilter = (type: string) => {
        setFilters(prev => ({
            ...prev,
            types: prev.types.includes(type)
                ? prev.types.filter(t => t !== type)
                : [...prev.types, type],
        }));
    };

    // Load more
    const handleLoadMore = () => {
        setPage(p => p + 1);
        fetchActivities(true);
    };

    return (
        <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm ${className}`}>
            {/* Header */}
            <div className="p-4 border-b dark:border-gray-700">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold">Activity Feed</h3>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setShowAggregation(!showAggregation)}
                            className={`px-3 py-1.5 text-sm rounded-md ${showAggregation ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                                }`}
                        >
                            📊 Aggregate
                        </button>
                        {showExport && (
                            <button
                                onClick={handleExport}
                                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200"
                            >
                                📥 Export CSV
                            </button>
                        )}
                    </div>
                </div>

                {/* Filters */}
                {showFilters && (
                    <div className="space-y-3">
                        {/* Search */}
                        <div className="relative">
                            <input
                                type="text"
                                value={filters.search}
                                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                                placeholder="Search activities..."
                                className="w-full pl-10 pr-4 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                            />
                            <svg className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </div>

                        {/* Type filters */}
                        <div className="flex flex-wrap gap-2">
                            {ACTIVITY_TYPES.map(type => (
                                <button
                                    key={type.value}
                                    onClick={() => toggleTypeFilter(type.value)}
                                    className={`px-2 py-1 text-xs rounded-full border ${filters.types.includes(type.value)
                                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                                            : 'border-gray-300 hover:border-gray-400'
                                        }`}
                                >
                                    {type.icon} {type.label}
                                </button>
                            ))}
                        </div>

                        {/* Date range */}
                        <div className="flex gap-2">
                            <input
                                type="date"
                                value={filters.dateFrom}
                                onChange={(e) => setFilters(prev => ({ ...prev, dateFrom: e.target.value }))}
                                className="px-3 py-1.5 text-sm border rounded-md dark:bg-gray-700 dark:border-gray-600"
                            />
                            <span className="text-gray-500 self-center">to</span>
                            <input
                                type="date"
                                value={filters.dateTo}
                                onChange={(e) => setFilters(prev => ({ ...prev, dateTo: e.target.value }))}
                                className="px-3 py-1.5 text-sm border rounded-md dark:bg-gray-700 dark:border-gray-600"
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Aggregation chart */}
            {showAggregation && aggregation.length > 0 && (
                <div className="p-4 border-b dark:border-gray-700">
                    <AggregationChart data={aggregation} />
                </div>
            )}

            {/* Error display */}
            {error && (
                <div className="m-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
                    {error}
                </div>
            )}

            {/* Activity list */}
            <div className="max-h-96 overflow-y-auto">
                {loading && activities.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">Loading activities...</div>
                ) : filteredActivities.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">No activities found</div>
                ) : (
                    filteredActivities.map(activity => (
                        <ActivityItem
                            key={activity.id}
                            activity={activity}
                            expanded={expandedId === activity.id}
                            onToggle={() => setExpandedId(expandedId === activity.id ? null : activity.id)}
                        />
                    ))
                )}
            </div>

            {/* Load more */}
            {hasMore && !loading && (
                <div className="p-4 border-t dark:border-gray-700 text-center">
                    <button
                        onClick={handleLoadMore}
                        className="px-4 py-2 text-sm text-blue-600 hover:underline"
                    >
                        Load more activities
                    </button>
                </div>
            )}

            {/* Footer stats */}
            <div className="px-4 py-2 border-t dark:border-gray-700 text-xs text-gray-500 flex justify-between">
                <span>Showing {filteredActivities.length} activities</span>
                {realTime && <span className="flex items-center gap-1">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    Live updates
                </span>}
            </div>
        </div>
    );
}

export default ActivityFeed;
