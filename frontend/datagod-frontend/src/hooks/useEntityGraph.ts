/**
 * useEntityGraph Hook
 * 
 * Custom hook for fetching, managing, and manipulating entity network graph data.
 * Supports depth control, node expansion, and layout algorithms.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';

// Type definitions
export interface GraphNode {
    id: string;
    type: 'person' | 'business' | 'property' | 'case' | 'vehicle' | 'unknown';
    label: string;
    subLabel?: string;
    data: Record<string, any>;
    x?: number;
    y?: number;
    fx?: number | null;
    fy?: number | null;
    expanded?: boolean;
    depth?: number;
    connectionCount?: number;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    label?: string;
    weight?: number;
    data?: Record<string, any>;
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

export interface GraphFilters {
    nodeTypes?: string[];
    edgeTypes?: string[];
    minConnections?: number;
    searchTerm?: string;
}

export interface LayoutOptions {
    algorithm: 'force' | 'radial' | 'hierarchical' | 'circular';
    nodeSpacing: number;
    preventOverlap: boolean;
}

export interface UseEntityGraphOptions {
    initialEntityId?: string;
    maxDepth?: number;
    autoExpand?: boolean;
    layoutOnLoad?: boolean;
}

export interface UseEntityGraphReturn {
    // Data
    graphData: GraphData;
    loading: boolean;
    error: Error | null;

    // Selected state
    selectedNode: GraphNode | null;
    selectedEdge: GraphEdge | null;

    // Actions
    loadEntity: (entityId: string) => Promise<void>;
    expandNode: (nodeId: string) => Promise<void>;
    collapseNode: (nodeId: string) => void;
    selectNode: (node: GraphNode | null) => void;
    selectEdge: (edge: GraphEdge | null) => void;

    // Filters
    filters: GraphFilters;
    setFilters: (filters: GraphFilters) => void;
    filteredData: GraphData;

    // Layout
    layoutOptions: LayoutOptions;
    setLayoutOptions: (options: Partial<LayoutOptions>) => void;
    applyLayout: () => void;

    // Utilities
    getNodeById: (id: string) => GraphNode | undefined;
    getConnectedNodes: (nodeId: string) => GraphNode[];
    getEdgesBetween: (sourceId: string, targetId: string) => GraphEdge[];
    exportData: (format: 'json' | 'csv') => string;

    // Stats
    stats: {
        totalNodes: number;
        totalEdges: number;
        nodesByType: Record<string, number>;
        avgConnections: number;
    };
}

const DEFAULT_LAYOUT: LayoutOptions = {
    algorithm: 'force',
    nodeSpacing: 100,
    preventOverlap: true,
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

/**
 * Fetch related entities for a given entity ID
 */
async function fetchEntityData(entityId: string, depth: number = 1): Promise<GraphData> {
    try {
        const response = await fetch(`${API_BASE_URL}/entities/${entityId}/network?depth=${depth}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch entity data: ${response.statusText}`);
        }

        const data = await response.json();
        return {
            nodes: data.nodes || [],
            edges: data.edges || data.relationships || [],
        };
    } catch (error) {
        console.error('Error fetching entity data:', error);
        throw error;
    }
}

/**
 * Apply layout algorithm to nodes
 */
function applyLayoutAlgorithm(
    nodes: GraphNode[],
    edges: GraphEdge[],
    options: LayoutOptions
): GraphNode[] {
    const centerX = 400;
    const centerY = 300;

    switch (options.algorithm) {
        case 'circular':
            return applyCircularLayout(nodes, centerX, centerY, options.nodeSpacing);

        case 'radial':
            return applyRadialLayout(nodes, edges, centerX, centerY, options.nodeSpacing);

        case 'hierarchical':
            return applyHierarchicalLayout(nodes, edges, options.nodeSpacing);

        case 'force':
        default:
            // Force layout is handled by D3 in the component
            return nodes.map((node, i) => ({
                ...node,
                x: node.x || centerX + Math.random() * 200 - 100,
                y: node.y || centerY + Math.random() * 200 - 100,
            }));
    }
}

function applyCircularLayout(
    nodes: GraphNode[],
    centerX: number,
    centerY: number,
    spacing: number
): GraphNode[] {
    const radius = Math.max(spacing * nodes.length / (2 * Math.PI), 150);

    return nodes.map((node, i) => {
        const angle = (2 * Math.PI * i) / nodes.length;
        return {
            ...node,
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
        };
    });
}

function applyRadialLayout(
    nodes: GraphNode[],
    edges: GraphEdge[],
    centerX: number,
    centerY: number,
    spacing: number
): GraphNode[] {
    // Group nodes by depth
    const depthGroups = new Map<number, GraphNode[]>();

    nodes.forEach(node => {
        const depth = node.depth || 0;
        if (!depthGroups.has(depth)) {
            depthGroups.set(depth, []);
        }
        depthGroups.get(depth)!.push(node);
    });

    const result: GraphNode[] = [];

    depthGroups.forEach((groupNodes, depth) => {
        const radius = depth * spacing;

        groupNodes.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / groupNodes.length;
            result.push({
                ...node,
                x: centerX + radius * Math.cos(angle),
                y: centerY + radius * Math.sin(angle),
            });
        });
    });

    return result;
}

function applyHierarchicalLayout(
    nodes: GraphNode[],
    edges: GraphEdge[],
    spacing: number
): GraphNode[] {
    // Group by depth
    const depthGroups = new Map<number, GraphNode[]>();

    nodes.forEach(node => {
        const depth = node.depth || 0;
        if (!depthGroups.has(depth)) {
            depthGroups.set(depth, []);
        }
        depthGroups.get(depth)!.push(node);
    });

    const result: GraphNode[] = [];
    let currentY = 50;

    // Sort depths
    const depths = Array.from(depthGroups.keys()).sort((a, b) => a - b);

    depths.forEach(depth => {
        const groupNodes = depthGroups.get(depth)!;
        const totalWidth = groupNodes.length * spacing;
        let currentX = 400 - totalWidth / 2;

        groupNodes.forEach(node => {
            result.push({
                ...node,
                x: currentX + spacing / 2,
                y: currentY,
            });
            currentX += spacing;
        });

        currentY += spacing;
    });

    return result;
}

/**
 * Main hook for entity graph data management
 */
export function useEntityGraph(options: UseEntityGraphOptions = {}): UseEntityGraphReturn {
    const {
        initialEntityId,
        maxDepth = 2,
        autoExpand = false,
        layoutOnLoad = true,
    } = options;

    // Core state
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    // Selection state
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);

    // Filter state
    const [filters, setFilters] = useState<GraphFilters>({});

    // Layout state
    const [layoutOptions, setLayoutOptionsState] = useState<LayoutOptions>(DEFAULT_LAYOUT);

    // Load initial entity
    useEffect(() => {
        if (initialEntityId) {
            loadEntity(initialEntityId);
        }
    }, [initialEntityId]);

    /**
     * Load an entity and its connections
     */
    const loadEntity = useCallback(async (entityId: string) => {
        setLoading(true);
        setError(null);

        try {
            const data = await fetchEntityData(entityId, maxDepth);

            // Mark root node
            const nodesWithDepth: GraphNode[] = data.nodes.map(node => ({
                ...node,
                depth: node.id === entityId ? 0 : 1,
                expanded: node.id === entityId,
            }));

            let finalNodes: GraphNode[] = nodesWithDepth;

            if (layoutOnLoad) {
                finalNodes = applyLayoutAlgorithm(nodesWithDepth, data.edges, layoutOptions);
            }

            setGraphData({
                nodes: finalNodes,
                edges: data.edges,
            });
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to load entity'));
        } finally {
            setLoading(false);
        }
    }, [maxDepth, layoutOnLoad, layoutOptions]);

    /**
     * Expand a node to show its connections
     */
    const expandNode = useCallback(async (nodeId: string) => {
        const node = graphData.nodes.find(n => n.id === nodeId);
        if (!node || node.expanded) return;

        setLoading(true);

        try {
            const data = await fetchEntityData(nodeId, 1);

            // Merge new nodes (avoid duplicates)
            const existingIds = new Set(graphData.nodes.map(n => n.id));
            const newNodes = data.nodes
                .filter(n => !existingIds.has(n.id))
                .map(n => ({
                    ...n,
                    depth: (node.depth || 0) + 1,
                    expanded: false,
                }));

            // Merge new edges
            const existingEdgeIds = new Set(graphData.edges.map(e => e.id));
            const newEdges = data.edges.filter(e => !existingEdgeIds.has(e.id));

            setGraphData(prev => ({
                nodes: [
                    ...prev.nodes.map(n => n.id === nodeId ? { ...n, expanded: true } : n),
                    ...newNodes,
                ],
                edges: [...prev.edges, ...newEdges],
            }));
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to expand node'));
        } finally {
            setLoading(false);
        }
    }, [graphData]);

    /**
     * Collapse a node (hide its children)
     */
    const collapseNode = useCallback((nodeId: string) => {
        const node = graphData.nodes.find(n => n.id === nodeId);
        if (!node) return;

        // Find all nodes that were added from this node
        const nodeDepth = node.depth || 0;
        const connectedEdges = graphData.edges.filter(
            e => e.source === nodeId || e.target === nodeId
        );
        const connectedIds = new Set(
            connectedEdges.flatMap(e => [e.source, e.target])
        );

        // Remove nodes with higher depth that are only connected to this node
        const nodesToRemove = new Set<string>();
        graphData.nodes.forEach(n => {
            if (n.id !== nodeId && (n.depth || 0) > nodeDepth) {
                // Check if this node is only connected through the collapsed node
                const nodeEdges = graphData.edges.filter(
                    e => e.source === n.id || e.target === n.id
                );
                const otherConnections = nodeEdges.filter(e => {
                    const otherId = e.source === n.id ? e.target : e.source;
                    return otherId !== nodeId && (graphData.nodes.find(x => x.id === otherId)?.depth || 0) <= nodeDepth;
                });

                if (otherConnections.length === 0) {
                    nodesToRemove.add(n.id);
                }
            }
        });

        setGraphData(prev => ({
            nodes: prev.nodes
                .filter(n => !nodesToRemove.has(n.id))
                .map(n => n.id === nodeId ? { ...n, expanded: false } : n),
            edges: prev.edges.filter(
                e => !nodesToRemove.has(e.source) && !nodesToRemove.has(e.target)
            ),
        }));
    }, [graphData]);

    /**
     * Apply filters to the graph data
     */
    const filteredData = useMemo<GraphData>(() => {
        let nodes = [...graphData.nodes];
        let edges = [...graphData.edges];

        // Filter by node types
        if (filters.nodeTypes && filters.nodeTypes.length > 0) {
            nodes = nodes.filter(n => filters.nodeTypes!.includes(n.type));
        }

        // Filter by edge types
        if (filters.edgeTypes && filters.edgeTypes.length > 0) {
            edges = edges.filter(e => filters.edgeTypes!.includes(e.type));
        }

        // Filter by minimum connections
        if (filters.minConnections && filters.minConnections > 0) {
            const connectionCounts = new Map<string, number>();
            edges.forEach(e => {
                connectionCounts.set(e.source, (connectionCounts.get(e.source) || 0) + 1);
                connectionCounts.set(e.target, (connectionCounts.get(e.target) || 0) + 1);
            });

            nodes = nodes.filter(n => (connectionCounts.get(n.id) || 0) >= filters.minConnections!);
        }

        // Filter by search term
        if (filters.searchTerm) {
            const term = filters.searchTerm.toLowerCase();
            nodes = nodes.filter(n =>
                n.label.toLowerCase().includes(term) ||
                n.subLabel?.toLowerCase().includes(term)
            );
        }

        // Remove edges that reference filtered-out nodes
        const nodeIds = new Set(nodes.map(n => n.id));
        edges = edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));

        return { nodes, edges };
    }, [graphData, filters]);

    /**
     * Apply layout to current nodes
     */
    const applyLayout = useCallback(() => {
        setGraphData(prev => ({
            ...prev,
            nodes: applyLayoutAlgorithm(prev.nodes, prev.edges, layoutOptions),
        }));
    }, [layoutOptions]);

    /**
     * Set layout options
     */
    const setLayoutOptions = useCallback((options: Partial<LayoutOptions>) => {
        setLayoutOptionsState(prev => ({ ...prev, ...options }));
    }, []);

    // Utility functions
    const getNodeById = useCallback((id: string) => {
        return graphData.nodes.find(n => n.id === id);
    }, [graphData.nodes]);

    const getConnectedNodes = useCallback((nodeId: string) => {
        const connectedIds = new Set<string>();

        graphData.edges.forEach(e => {
            if (e.source === nodeId) connectedIds.add(e.target);
            if (e.target === nodeId) connectedIds.add(e.source);
        });

        return graphData.nodes.filter(n => connectedIds.has(n.id));
    }, [graphData]);

    const getEdgesBetween = useCallback((sourceId: string, targetId: string) => {
        return graphData.edges.filter(
            e => (e.source === sourceId && e.target === targetId) ||
                (e.source === targetId && e.target === sourceId)
        );
    }, [graphData.edges]);

    const exportData = useCallback((format: 'json' | 'csv'): string => {
        if (format === 'json') {
            return JSON.stringify(graphData, null, 2);
        }

        // CSV format
        const nodesCsv = [
            ['id', 'type', 'label', 'subLabel'].join(','),
            ...graphData.nodes.map(n => [n.id, n.type, `"${n.label}"`, `"${n.subLabel || ''}"`].join(','))
        ].join('\n');

        const edgesCsv = [
            ['source', 'target', 'type', 'label'].join(','),
            ...graphData.edges.map(e => [e.source, e.target, e.type, `"${e.label || ''}"`].join(','))
        ].join('\n');

        return `NODES\n${nodesCsv}\n\nEDGES\n${edgesCsv}`;
    }, [graphData]);

    // Calculate stats
    const stats = useMemo(() => {
        const nodesByType: Record<string, number> = {};
        graphData.nodes.forEach(n => {
            nodesByType[n.type] = (nodesByType[n.type] || 0) + 1;
        });

        const totalConnections = graphData.edges.length * 2;
        const avgConnections = graphData.nodes.length > 0
            ? totalConnections / graphData.nodes.length
            : 0;

        return {
            totalNodes: graphData.nodes.length,
            totalEdges: graphData.edges.length,
            nodesByType,
            avgConnections: Math.round(avgConnections * 100) / 100,
        };
    }, [graphData]);

    return {
        graphData,
        loading,
        error,
        selectedNode,
        selectedEdge,
        loadEntity,
        expandNode,
        collapseNode,
        selectNode: setSelectedNode,
        selectEdge: setSelectedEdge,
        filters,
        setFilters,
        filteredData,
        layoutOptions,
        setLayoutOptions,
        applyLayout,
        getNodeById,
        getConnectedNodes,
        getEdgesBetween,
        exportData,
        stats,
    };
}

export default useEntityGraph;
