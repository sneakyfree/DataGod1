'use client';

import { useState, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v2';

// Generic fetch wrapper
async function api<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// =============================================================================
// AGENT HOOKS
// =============================================================================

export interface AgentQueryResult {
    task_id: string;
    status: string;
    result: Record<string, any> | null;
    confidence: number | null;
    agents_consulted: string[];
    requires_approval: boolean;
    timestamp: string;
}

export function useAgentQuery() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<AgentQueryResult | null>(null);

    const query = useCallback(async (queryText: string, context: Record<string, any> = {}) => {
        setLoading(true);
        setError(null);
        try {
            const data = await api<AgentQueryResult>('/agents/query', {
                method: 'POST',
                body: JSON.stringify({ query: queryText, context }),
            });
            setResult(data);
            return data;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Query failed';
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const propertySearch = useCallback(async (params: {
        address?: string;
        parcel_id?: string;
        county?: string;
        state: string;
    }) => {
        setLoading(true);
        setError(null);
        try {
            const data = await api<AgentQueryResult>('/agents/property', {
                method: 'POST',
                body: JSON.stringify(params),
            });
            setResult(data);
            return data;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Property search failed';
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return { query, propertySearch, loading, error, result };
}

// =============================================================================
// INTELLIGENCE HOOKS
// =============================================================================

export interface ScenarioResult {
    scenario_id: string;
    scenario_name: string;
    category: string;
    confidence: string;
    confidence_score: number;
    description: string;
    recommended_actions: string[];
}

export interface ScenarioAnalysis {
    total_scenarios: number;
    high_confidence_count: number;
    by_category: Record<string, number>;
    scenarios: ScenarioResult[];
    summary: Record<string, any>;
    timestamp: string;
}

export function useScenarioAnalysis() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<ScenarioAnalysis | null>(null);

    const analyze = useCallback(async (data: {
        property_data?: Record<string, any>;
        entity_data?: Record<string, any>;
        lien_data?: Record<string, any>;
        risk_data?: Record<string, any>;
    }) => {
        setLoading(true);
        setError(null);
        try {
            const response = await api<ScenarioAnalysis>('/intelligence/scenarios', {
                method: 'POST',
                body: JSON.stringify(data),
            });
            setResult(response);
            return response;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Analysis failed';
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return { analyze, loading, error, result };
}

export interface BlockerResult {
    blocker_id: string;
    blocker_type: string;
    name: string;
    severity: string;
    why_not: string;
    priority_score: number;
}

export interface BlockerAnalysis {
    total_blockers: number;
    critical_count: number;
    high_count: number;
    blockers: BlockerResult[];
    fix_list: Record<string, any[]>;
    unlockers: Record<string, any>[];
    timestamp: string;
}

export function useBlockerAnalysis() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<BlockerAnalysis | null>(null);

    const analyze = useCallback(async (data: {
        property_data?: Record<string, any>;
        lien_data?: Record<string, any>;
        title_data?: Record<string, any>;
        legal_data?: Record<string, any>;
    }) => {
        setLoading(true);
        setError(null);
        try {
            const response = await api<BlockerAnalysis>('/intelligence/blockers', {
                method: 'POST',
                body: JSON.stringify(data),
            });
            setResult(response);
            return response;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Analysis failed';
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return { analyze, loading, error, result };
}

// =============================================================================
// INTAKE HOOKS
// =============================================================================

export interface IntakeSession {
    session_id: string;
    schema_name: string;
    total_stages: number;
    current_stage: number;
    fields: any[];
    groups: any[];
}

export interface StageSubmitResult {
    session_id: string;
    current_stage: number;
    validations: any[];
    contradictions: any[];
    verification_tasks: any[];
    can_proceed: boolean;
    next_stage?: number;
    next_fields?: any[];
    complete: boolean;
    final_data?: Record<string, any>;
}

export function useIntakeSession() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [session, setSession] = useState<IntakeSession | null>(null);

    const startSession = useCallback(async (schemaId: string) => {
        setLoading(true);
        setError(null);
        try {
            const data = await api<IntakeSession>('/intake/start', {
                method: 'POST',
                body: JSON.stringify({ schema_id: schemaId }),
            });
            setSession(data);
            return data;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to start session';
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const submitStage = useCallback(async (sessionId: string, data: Record<string, any>) => {
        setLoading(true);
        setError(null);
        try {
            const result = await api<StageSubmitResult>(`/intake/${sessionId}/submit`, {
                method: 'POST',
                body: JSON.stringify({ data }),
            });
            return result;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to submit stage';
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return { startSession, submitStage, loading, error, session };
}

// =============================================================================
// REPORT HOOKS
// =============================================================================

export type ReportView = 'consumer' | 'operator' | 'analyst' | 'audit';
export type ExportFormat = 'json' | 'html' | 'markdown' | 'pdf';

export interface ReportSection {
    id: string;
    title: string;
    content: Record<string, any>;
    description?: string;
    order: number;
}

export interface Report {
    report_id: string;
    title: string;
    view: string;
    generated_at: string;
    sections: ReportSection[];
    disclaimer: string;
    footer: Record<string, any>;
}

export function useReport() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [report, setReport] = useState<Report | null>(null);

    const generate = useCallback(async (data: Record<string, any>, view: ReportView = 'consumer', title?: string) => {
        setLoading(true);
        setError(null);
        try {
            const result = await api<Report>('/reports/generate', {
                method: 'POST',
                body: JSON.stringify({ data, view, title }),
            });
            setReport(result);
            return result;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to generate report';
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const exportReport = useCallback(async (reportId: string, format: ExportFormat) => {
        const response = await fetch(`${API_BASE}/reports/${reportId}/export?format=${format}`);
        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report_${reportId}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }, []);

    return { generate, exportReport, loading, error, report };
}
