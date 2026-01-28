/**
 * Error Handling Utilities
 * 
 * Global error boundary, API retry logic, offline detection,
 * and user-friendly error messages.
 */

'use client';

import React, { Component, createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// Types
interface ErrorDetails {
    code?: string;
    message: string;
    details?: string;
    retryable: boolean;
    timestamp: Date;
    context?: Record<string, any>;
}

interface RetryConfig {
    maxRetries: number;
    initialDelayMs: number;
    maxDelayMs: number;
    backoffMultiplier: number;
    retryableStatuses: number[];
}

interface ErrorContextType {
    errors: ErrorDetails[];
    addError: (error: ErrorDetails) => void;
    clearErrors: () => void;
    isOffline: boolean;
    lastError: ErrorDetails | null;
}

// Default retry config
const DEFAULT_RETRY_CONFIG: RetryConfig = {
    maxRetries: 3,
    initialDelayMs: 1000,
    maxDelayMs: 10000,
    backoffMultiplier: 2,
    retryableStatuses: [408, 429, 500, 502, 503, 504],
};

// Error messages by code
const ERROR_MESSAGES: Record<string, string> = {
    NETWORK_ERROR: 'Unable to connect. Please check your internet connection.',
    TIMEOUT: 'The request took too long. Please try again.',
    UNAUTHORIZED: 'Your session has expired. Please log in again.',
    FORBIDDEN: 'You don\'t have permission to perform this action.',
    NOT_FOUND: 'The requested resource was not found.',
    RATE_LIMITED: 'Too many requests. Please wait a moment.',
    SERVER_ERROR: 'Something went wrong on our end. We\'re working on it.',
    VALIDATION_ERROR: 'Please check your input and try again.',
    OFFLINE: 'You appear to be offline. Changes will sync when you reconnect.',
    DEFAULT: 'An unexpected error occurred. Please try again.',
};

// Error Context
const ErrorContext = createContext<ErrorContextType | null>(null);

export function useError() {
    const context = useContext(ErrorContext);
    if (!context) {
        throw new Error('useError must be used within ErrorProvider');
    }
    return context;
}

// Error Provider Component
export function ErrorProvider({ children }: { children: ReactNode }) {
    const [errors, setErrors] = useState<ErrorDetails[]>([]);
    const [isOffline, setIsOffline] = useState(false);

    // Online/offline detection
    useEffect(() => {
        const handleOnline = () => setIsOffline(false);
        const handleOffline = () => setIsOffline(true);

        setIsOffline(!navigator.onLine);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    const addError = useCallback((error: ErrorDetails) => {
        setErrors(prev => [error, ...prev.slice(0, 9)]); // Keep last 10 errors
    }, []);

    const clearErrors = useCallback(() => {
        setErrors([]);
    }, []);

    const lastError = errors[0] || null;

    return (
        <ErrorContext.Provider value={{ errors, addError, clearErrors, isOffline, lastError }}>
            {children}
        </ErrorContext.Provider>
    );
}

// Error Boundary Class Component
interface ErrorBoundaryProps {
    children: ReactNode;
    fallback?: ReactNode;
    onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
    errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        this.setState({ errorInfo });

        if (this.props.onError) {
            this.props.onError(error, errorInfo);
        }

        // Log to error tracking service
        console.error('Error Boundary caught error:', error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
                    <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 text-center">
                        <div className="text-6xl mb-4">😵</div>
                        <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
                        <p className="text-gray-600 dark:text-gray-400 mb-4">
                            We encountered an unexpected error. Please try refreshing the page.
                        </p>
                        {this.state.error && (
                            <details className="text-left mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm">
                                <summary className="cursor-pointer font-medium">Error details</summary>
                                <pre className="mt-2 overflow-auto text-xs">
                                    {this.state.error.message}
                                </pre>
                            </details>
                        )}
                        <div className="flex gap-2 justify-center">
                            <button
                                onClick={this.handleReset}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                            >
                                Try Again
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                            >
                                Refresh Page
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

// API Fetch with Retry
export async function fetchWithRetry<T>(
    url: string,
    options: RequestInit = {},
    config: Partial<RetryConfig> = {}
): Promise<T> {
    const retryConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
    let lastError: Error | null = null;
    let delay = retryConfig.initialDelayMs;

    for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const shouldRetry = retryConfig.retryableStatuses.includes(response.status) &&
                    attempt < retryConfig.maxRetries;

                if (shouldRetry) {
                    await sleep(delay);
                    delay = Math.min(delay * retryConfig.backoffMultiplier, retryConfig.maxDelayMs);
                    continue;
                }

                throw new APIError(
                    getErrorMessage(response.status),
                    response.status,
                    await response.text().catch(() => '')
                );
            }

            return await response.json();
        } catch (error) {
            lastError = error as Error;

            if (error instanceof DOMException && error.name === 'AbortError') {
                throw new APIError(ERROR_MESSAGES.TIMEOUT, 408, 'Request timeout');
            }

            if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                if (attempt < retryConfig.maxRetries) {
                    await sleep(delay);
                    delay = Math.min(delay * retryConfig.backoffMultiplier, retryConfig.maxDelayMs);
                    continue;
                }
                throw new APIError(ERROR_MESSAGES.NETWORK_ERROR, 0, 'Network error');
            }

            throw error;
        }
    }

    throw lastError || new Error('Unknown error');
}

// Custom API Error class
export class APIError extends Error {
    constructor(
        message: string,
        public statusCode: number,
        public details?: string
    ) {
        super(message);
        this.name = 'APIError';
    }

    get isRetryable(): boolean {
        return DEFAULT_RETRY_CONFIG.retryableStatuses.includes(this.statusCode);
    }

    toErrorDetails(): ErrorDetails {
        return {
            code: String(this.statusCode),
            message: this.message,
            details: this.details,
            retryable: this.isRetryable,
            timestamp: new Date(),
        };
    }
}

// Get user-friendly error message
function getErrorMessage(statusCode: number): string {
    switch (statusCode) {
        case 401: return ERROR_MESSAGES.UNAUTHORIZED;
        case 403: return ERROR_MESSAGES.FORBIDDEN;
        case 404: return ERROR_MESSAGES.NOT_FOUND;
        case 408: return ERROR_MESSAGES.TIMEOUT;
        case 422: return ERROR_MESSAGES.VALIDATION_ERROR;
        case 429: return ERROR_MESSAGES.RATE_LIMITED;
        case 500:
        case 502:
        case 503:
        case 504: return ERROR_MESSAGES.SERVER_ERROR;
        default: return ERROR_MESSAGES.DEFAULT;
    }
}

// Sleep utility
function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Toast notification for errors
export function ErrorToast({ error, onDismiss }: { error: ErrorDetails; onDismiss: () => void }) {
    return (
        <div className="fixed bottom-4 right-4 max-w-sm bg-red-50 dark:bg-red-900/90 border border-red-200 dark:border-red-800 rounded-lg shadow-lg p-4 animate-slide-up">
            <div className="flex items-start gap-3">
                <div className="text-red-500 text-xl">⚠️</div>
                <div className="flex-1">
                    <p className="font-medium text-red-800 dark:text-red-200">{error.message}</p>
                    {error.details && (
                        <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error.details}</p>
                    )}
                    {error.retryable && (
                        <p className="text-xs text-red-500 mt-2">This action can be retried</p>
                    )}
                </div>
                <button onClick={onDismiss} className="text-red-400 hover:text-red-600">
                    ✕
                </button>
            </div>
        </div>
    );
}

// Offline Banner
export function OfflineBanner() {
    const { isOffline } = useError();

    if (!isOffline) return null;

    return (
        <div className="fixed top-0 left-0 right-0 bg-yellow-500 text-yellow-900 px-4 py-2 text-center text-sm font-medium z-50">
            <span className="mr-2">📡</span>
            You're offline. Some features may be unavailable.
        </div>
    );
}

// Hook for API calls with error handling
export function useAPICall<T>() {
    const { addError } = useError();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<ErrorDetails | null>(null);

    const execute = useCallback(async (
        apiCall: () => Promise<T>,
        options: { showToast?: boolean; retryConfig?: Partial<RetryConfig> } = {}
    ): Promise<T | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await apiCall();
            return result;
        } catch (err) {
            const errorDetails: ErrorDetails = err instanceof APIError
                ? err.toErrorDetails()
                : {
                    message: err instanceof Error ? err.message : 'Unknown error',
                    retryable: false,
                    timestamp: new Date(),
                };

            setError(errorDetails);

            if (options.showToast !== false) {
                addError(errorDetails);
            }

            return null;
        } finally {
            setLoading(false);
        }
    }, [addError]);

    return { execute, loading, error };
}

// Graceful degradation component
export function GracefulDegradation({
    children,
    fallback,
    condition,
}: {
    children: ReactNode;
    fallback: ReactNode;
    condition: boolean;
}) {
    return condition ? <>{children}</> : <>{fallback}</>;
}

export default ErrorBoundary;
