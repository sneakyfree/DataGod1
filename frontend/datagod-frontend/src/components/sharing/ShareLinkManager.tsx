/**
 * ShareLinkManager Component
 * 
 * Enhanced share link system with password protection, expiry countdown,
 * view analytics, email sharing, and social preview (Open Graph).
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface ShareLink {
    id: string;
    url: string;
    shortCode: string;
    targetType: 'report' | 'dashboard' | 'entity' | 'search';
    targetId: string;
    title: string;
    createdAt: string;
    expiresAt?: string;
    passwordProtected: boolean;
    viewCount: number;
    lastViewed?: string;
    createdBy: string;
    settings: ShareSettings;
}

interface ShareSettings {
    allowDownload: boolean;
    showBranding: boolean;
    requireEmail: boolean;
    notifyOnView: boolean;
    maxViews?: number;
    ogTitle?: string;
    ogDescription?: string;
    ogImage?: string;
}

interface ViewAnalytics {
    totalViews: number;
    uniqueViews: number;
    viewsByDate: { date: string; count: number }[];
    viewsByLocation: { country: string; count: number }[];
    viewsByDevice: { device: string; count: number }[];
    recentViews: { viewedAt: string; location?: string; device?: string }[];
}

interface ShareLinkManagerProps {
    targetType: 'report' | 'dashboard' | 'entity' | 'search';
    targetId: string;
    title: string;
    onClose?: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

// Time formatting utilities
const formatRelativeTime = (date: string): string => {
    const now = new Date();
    const target = new Date(date);
    const diffMs = target.getTime() - now.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMs <= 0) return 'Expired';
    if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} left`;
    if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} left`;
    return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} left`;
};

const formatDate = (date: string): string => {
    return new Date(date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
};

// Tab Button Component
const TabButton = ({
    active,
    onClick,
    children
}: {
    active: boolean;
    onClick: () => void;
    children: React.ReactNode;
}) => (
    <button
        onClick={onClick}
        className={`px-4 py-2 text-sm font-medium rounded-t-lg ${active
                ? 'bg-white dark:bg-gray-800 border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
    >
        {children}
    </button>
);

// Copy Button Component
const CopyButton = ({ text }: { text: string }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            onClick={handleCopy}
            className="px-3 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 flex items-center gap-1"
        >
            {copied ? (
                <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Copied
                </>
            ) : (
                <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                </>
            )}
        </button>
    );
};

// Analytics Chart (simplified)
const MiniChart = ({ data }: { data: { date: string; count: number }[] }) => {
    if (!data.length) return <div className="text-gray-400 text-sm">No views yet</div>;

    const maxCount = Math.max(...data.map(d => d.count));

    return (
        <div className="flex items-end gap-1 h-16">
            {data.slice(-14).map((d, i) => (
                <div
                    key={i}
                    className="flex-1 bg-blue-500 rounded-t min-w-1"
                    style={{ height: `${maxCount > 0 ? (d.count / maxCount) * 100 : 0}%`, minHeight: d.count > 0 ? '4px' : '0' }}
                    title={`${d.date}: ${d.count} views`}
                />
            ))}
        </div>
    );
};

export function ShareLinkManager({
    targetType,
    targetId,
    title,
    onClose,
}: ShareLinkManagerProps) {
    // State
    const [activeTab, setActiveTab] = useState<'create' | 'manage' | 'analytics'>('create');
    const [links, setLinks] = useState<ShareLink[]>([]);
    const [selectedLink, setSelectedLink] = useState<ShareLink | null>(null);
    const [analytics, setAnalytics] = useState<ViewAnalytics | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Create form state
    const [formData, setFormData] = useState({
        password: '',
        usePassword: false,
        expiryDays: 7,
        useExpiry: true,
        allowDownload: true,
        showBranding: true,
        requireEmail: false,
        notifyOnView: false,
        maxViews: 0,
        ogTitle: title,
        ogDescription: '',
    });

    // Email sharing state
    const [emailData, setEmailData] = useState({
        to: '',
        subject: `Shared: ${title}`,
        message: '',
    });
    const [showEmailForm, setShowEmailForm] = useState(false);

    // Fetch existing links
    const fetchLinks = useCallback(async () => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/share-links?targetType=${targetType}&targetId=${targetId}`,
                {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                    },
                }
            );

            if (response.ok) {
                const data = await response.json();
                setLinks(data.links || []);
            }
        } catch (err) {
            console.error('Failed to fetch links:', err);
        }
    }, [targetType, targetId]);

    // Fetch analytics for a link
    const fetchAnalytics = useCallback(async (linkId: string) => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/share-links/${linkId}/analytics`,
                {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                    },
                }
            );

            if (response.ok) {
                const data = await response.json();
                setAnalytics(data);
            }
        } catch (err) {
            console.error('Failed to fetch analytics:', err);
        }
    }, []);

    useEffect(() => {
        fetchLinks();
    }, [fetchLinks]);

    useEffect(() => {
        if (selectedLink) {
            fetchAnalytics(selectedLink.id);
        }
    }, [selectedLink, fetchAnalytics]);

    // Create new share link
    const handleCreate = async () => {
        setLoading(true);
        setError(null);

        try {
            const expiresAt = formData.useExpiry
                ? new Date(Date.now() + formData.expiryDays * 24 * 60 * 60 * 1000).toISOString()
                : null;

            const response = await fetch(`${API_BASE_URL}/share-links`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    targetType,
                    targetId,
                    title,
                    password: formData.usePassword ? formData.password : null,
                    expiresAt,
                    settings: {
                        allowDownload: formData.allowDownload,
                        showBranding: formData.showBranding,
                        requireEmail: formData.requireEmail,
                        notifyOnView: formData.notifyOnView,
                        maxViews: formData.maxViews > 0 ? formData.maxViews : null,
                        ogTitle: formData.ogTitle,
                        ogDescription: formData.ogDescription,
                    },
                }),
            });

            if (!response.ok) throw new Error('Failed to create share link');

            const newLink = await response.json();
            setLinks(prev => [newLink, ...prev]);
            setSelectedLink(newLink);
            setActiveTab('manage');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create link');
        } finally {
            setLoading(false);
        }
    };

    // Delete share link
    const handleDelete = async (linkId: string) => {
        if (!confirm('Are you sure you want to delete this share link?')) return;

        try {
            const response = await fetch(`${API_BASE_URL}/share-links/${linkId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                },
            });

            if (response.ok) {
                setLinks(prev => prev.filter(l => l.id !== linkId));
                if (selectedLink?.id === linkId) {
                    setSelectedLink(null);
                }
            }
        } catch (err) {
            console.error('Failed to delete link:', err);
        }
    };

    // Send email share
    const handleSendEmail = async () => {
        if (!selectedLink || !emailData.to) return;

        setLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/share-links/${selectedLink.id}/send-email`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(emailData),
            });

            if (!response.ok) throw new Error('Failed to send email');

            setShowEmailForm(false);
            setEmailData({ to: '', subject: `Shared: ${title}`, message: '' });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to send email');
        } finally {
            setLoading(false);
        }
    };

    // Social share URLs
    const getSocialShareUrl = (platform: string, url: string) => {
        const encodedUrl = encodeURIComponent(url);
        const encodedTitle = encodeURIComponent(title);

        switch (platform) {
            case 'twitter':
                return `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`;
            case 'linkedin':
                return `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`;
            case 'facebook':
                return `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`;
            default:
                return url;
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
                <h2 className="text-lg font-semibold">Share: {title}</h2>
                {onClose && (
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Tabs */}
            <div className="flex border-b dark:border-gray-700 px-4">
                <TabButton active={activeTab === 'create'} onClick={() => setActiveTab('create')}>
                    Create Link
                </TabButton>
                <TabButton active={activeTab === 'manage'} onClick={() => setActiveTab('manage')}>
                    Manage ({links.length})
                </TabButton>
                {selectedLink && (
                    <TabButton active={activeTab === 'analytics'} onClick={() => setActiveTab('analytics')}>
                        Analytics
                    </TabButton>
                )}
            </div>

            {/* Error display */}
            {error && (
                <div className="mx-4 mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
                    {error}
                </div>
            )}

            {/* Content */}
            <div className="p-4">
                {/* Create Tab */}
                {activeTab === 'create' && (
                    <div className="space-y-4">
                        {/* Password Protection */}
                        <div className="flex items-start gap-3">
                            <input
                                type="checkbox"
                                checked={formData.usePassword}
                                onChange={(e) => setFormData(prev => ({ ...prev, usePassword: e.target.checked }))}
                                className="mt-1 rounded"
                            />
                            <div className="flex-1">
                                <label className="font-medium">Password Protection</label>
                                <p className="text-sm text-gray-500">Require a password to view</p>
                                {formData.usePassword && (
                                    <input
                                        type="text"
                                        value={formData.password}
                                        onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                                        placeholder="Enter password"
                                        className="mt-2 w-full px-3 py-2 border rounded-md dark:bg-gray-700"
                                    />
                                )}
                            </div>
                        </div>

                        {/* Expiration */}
                        <div className="flex items-start gap-3">
                            <input
                                type="checkbox"
                                checked={formData.useExpiry}
                                onChange={(e) => setFormData(prev => ({ ...prev, useExpiry: e.target.checked }))}
                                className="mt-1 rounded"
                            />
                            <div className="flex-1">
                                <label className="font-medium">Set Expiration</label>
                                <p className="text-sm text-gray-500">Link will expire after this time</p>
                                {formData.useExpiry && (
                                    <select
                                        value={formData.expiryDays}
                                        onChange={(e) => setFormData(prev => ({ ...prev, expiryDays: parseInt(e.target.value) }))}
                                        className="mt-2 px-3 py-2 border rounded-md dark:bg-gray-700"
                                    >
                                        <option value={1}>1 day</option>
                                        <option value={7}>7 days</option>
                                        <option value={30}>30 days</option>
                                        <option value={90}>90 days</option>
                                    </select>
                                )}
                            </div>
                        </div>

                        {/* Additional Options */}
                        <div className="grid grid-cols-2 gap-4">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={formData.allowDownload}
                                    onChange={(e) => setFormData(prev => ({ ...prev, allowDownload: e.target.checked }))}
                                    className="rounded"
                                />
                                <span className="text-sm">Allow download</span>
                            </label>

                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={formData.notifyOnView}
                                    onChange={(e) => setFormData(prev => ({ ...prev, notifyOnView: e.target.checked }))}
                                    className="rounded"
                                />
                                <span className="text-sm">Notify on view</span>
                            </label>

                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={formData.requireEmail}
                                    onChange={(e) => setFormData(prev => ({ ...prev, requireEmail: e.target.checked }))}
                                    className="rounded"
                                />
                                <span className="text-sm">Require email</span>
                            </label>

                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={formData.showBranding}
                                    onChange={(e) => setFormData(prev => ({ ...prev, showBranding: e.target.checked }))}
                                    className="rounded"
                                />
                                <span className="text-sm">Show branding</span>
                            </label>
                        </div>

                        {/* Social Preview (Open Graph) */}
                        <div className="border-t pt-4">
                            <h4 className="font-medium mb-2">Social Preview</h4>
                            <input
                                type="text"
                                value={formData.ogTitle}
                                onChange={(e) => setFormData(prev => ({ ...prev, ogTitle: e.target.value }))}
                                placeholder="Preview title"
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 mb-2"
                            />
                            <textarea
                                value={formData.ogDescription}
                                onChange={(e) => setFormData(prev => ({ ...prev, ogDescription: e.target.value }))}
                                placeholder="Preview description (optional)"
                                rows={2}
                                className="w-full px-3 py-2 border rounded-md dark:bg-gray-700"
                            />
                        </div>

                        <button
                            onClick={handleCreate}
                            disabled={loading}
                            className="w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                            {loading ? 'Creating...' : 'Create Share Link'}
                        </button>
                    </div>
                )}

                {/* Manage Tab */}
                {activeTab === 'manage' && (
                    <div className="space-y-4">
                        {links.length === 0 ? (
                            <p className="text-center text-gray-500 py-8">No share links created yet</p>
                        ) : (
                            links.map(link => (
                                <div
                                    key={link.id}
                                    className={`p-4 border rounded-lg cursor-pointer ${selectedLink?.id === link.id ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''
                                        }`}
                                    onClick={() => setSelectedLink(link)}
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="font-medium">{link.shortCode}</span>
                                                {link.passwordProtected && (
                                                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                                                        🔒 Protected
                                                    </span>
                                                )}
                                                {link.expiresAt && (
                                                    <span className={`text-xs px-2 py-0.5 rounded ${new Date(link.expiresAt) > new Date()
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-red-100 text-red-800'
                                                        }`}>
                                                        {formatRelativeTime(link.expiresAt)}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-500">
                                                {link.viewCount} views • Created {formatDate(link.createdAt)}
                                            </p>
                                        </div>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); handleDelete(link.id); }}
                                            className="text-red-500 hover:text-red-700"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>

                                    {selectedLink?.id === link.id && (
                                        <div className="mt-4 pt-4 border-t">
                                            <div className="flex mb-3">
                                                <input
                                                    type="text"
                                                    value={link.url}
                                                    readOnly
                                                    className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 border rounded-l-md"
                                                />
                                                <CopyButton text={link.url} />
                                            </div>

                                            {/* Social share buttons */}
                                            <div className="flex gap-2 mb-3">
                                                <a
                                                    href={getSocialShareUrl('twitter', link.url)}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="px-3 py-1.5 bg-[#1DA1F2] text-white rounded text-sm"
                                                >
                                                    Twitter
                                                </a>
                                                <a
                                                    href={getSocialShareUrl('linkedin', link.url)}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="px-3 py-1.5 bg-[#0A66C2] text-white rounded text-sm"
                                                >
                                                    LinkedIn
                                                </a>
                                                <button
                                                    onClick={() => setShowEmailForm(!showEmailForm)}
                                                    className="px-3 py-1.5 bg-gray-600 text-white rounded text-sm"
                                                >
                                                    Email
                                                </button>
                                            </div>

                                            {/* Email form */}
                                            {showEmailForm && (
                                                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md space-y-2">
                                                    <input
                                                        type="email"
                                                        value={emailData.to}
                                                        onChange={(e) => setEmailData(prev => ({ ...prev, to: e.target.value }))}
                                                        placeholder="Recipient email"
                                                        className="w-full px-3 py-2 border rounded-md dark:bg-gray-600"
                                                    />
                                                    <textarea
                                                        value={emailData.message}
                                                        onChange={(e) => setEmailData(prev => ({ ...prev, message: e.target.value }))}
                                                        placeholder="Personal message (optional)"
                                                        rows={2}
                                                        className="w-full px-3 py-2 border rounded-md dark:bg-gray-600"
                                                    />
                                                    <button
                                                        onClick={handleSendEmail}
                                                        disabled={loading || !emailData.to}
                                                        className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:opacity-50"
                                                    >
                                                        {loading ? 'Sending...' : 'Send Email'}
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                )}

                {/* Analytics Tab */}
                {activeTab === 'analytics' && selectedLink && (
                    <div className="space-y-6">
                        {/* Overview Stats */}
                        <div className="grid grid-cols-3 gap-4">
                            <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg text-center">
                                <div className="text-2xl font-bold">{analytics?.totalViews || 0}</div>
                                <div className="text-sm text-gray-500">Total Views</div>
                            </div>
                            <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg text-center">
                                <div className="text-2xl font-bold">{analytics?.uniqueViews || 0}</div>
                                <div className="text-sm text-gray-500">Unique Views</div>
                            </div>
                            <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg text-center">
                                <div className="text-2xl font-bold">
                                    {selectedLink.expiresAt ? formatRelativeTime(selectedLink.expiresAt) : '∞'}
                                </div>
                                <div className="text-sm text-gray-500">Time Left</div>
                            </div>
                        </div>

                        {/* Views Chart */}
                        <div>
                            <h4 className="font-medium mb-2">Views Over Time</h4>
                            <MiniChart data={analytics?.viewsByDate || []} />
                        </div>

                        {/* Recent Views */}
                        {analytics?.recentViews && analytics.recentViews.length > 0 && (
                            <div>
                                <h4 className="font-medium mb-2">Recent Views</h4>
                                <div className="space-y-2">
                                    {analytics.recentViews.slice(0, 5).map((view, i) => (
                                        <div key={i} className="flex justify-between text-sm">
                                            <span>{formatDate(view.viewedAt)}</span>
                                            <span className="text-gray-500">{view.location || 'Unknown'} • {view.device || 'Unknown'}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

export default ShareLinkManager;
