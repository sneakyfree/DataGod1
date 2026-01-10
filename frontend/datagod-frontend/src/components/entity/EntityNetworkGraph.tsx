'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
} from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import HomeIcon from '@mui/icons-material/Home';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

interface Entity {
  id: number;
  entity_name: string;
  entity_type: 'person' | 'company' | 'property';
  address?: string;
  city?: string;
  state?: string;
}

interface Relationship {
  id: number;
  entity1_id: number;
  entity2_id: number;
  relationship_type: string;
  confidence_score: number;
  role1?: string;
  role2?: string;
}

interface NetworkNode {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  entity: Entity;
  isCenter: boolean;
}

interface NetworkEdge {
  source: number;
  target: number;
  relationship: Relationship;
}

interface EntityNetworkGraphProps {
  centerId?: number;
  depth?: number;
  width?: number;
  height?: number;
  onNodeClick?: (entity: Entity) => void;
  onEdgeClick?: (relationship: Relationship) => void;
}

const entityColors = {
  person: '#2196F3',
  company: '#4CAF50',
  property: '#FF9800',
};

const EntityIcon = ({ type, size = 24 }: { type: string; size?: number }) => {
  switch (type) {
    case 'person':
      return <PersonIcon sx={{ fontSize: size }} />;
    case 'company':
      return <BusinessIcon sx={{ fontSize: size }} />;
    case 'property':
      return <HomeIcon sx={{ fontSize: size }} />;
    default:
      return <PersonIcon sx={{ fontSize: size }} />;
  }
};

export const EntityNetworkGraph = ({
  centerId,
  depth = 2,
  width = 800,
  height = 600,
  onNodeClick,
  onEdgeClick,
}: EntityNetworkGraphProps) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [edges, setEdges] = useState<NetworkEdge[]>([]);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragNode, setDragNode] = useState<NetworkNode | null>(null);

  // Fetch network data from the real API
  const { data: networkData, isLoading, error } = useQuery({
    queryKey: ['entityNetwork', centerId, depth],
    queryFn: async () => {
      if (!centerId) return null;
      try {
        const response = await apiService.getEntityNetwork(String(centerId), depth);
        // Transform API response to component format
        const { nodes, edges } = response.data;
        return {
          entities: nodes.map((node: any) => ({
            id: node.id,
            entity_name: node.name,
            entity_type: node.type,
            address: node.address,
            city: node.city,
            state: node.state,
          })),
          relationships: edges.map((edge: any) => ({
            id: edge.id,
            entity1_id: edge.source,
            entity2_id: edge.target,
            relationship_type: edge.type,
            confidence_score: edge.confidence || 1.0,
            role1: edge.role1,
            role2: edge.role2,
          })),
        };
      } catch (err) {
        // Fallback to mock data for demo
        console.warn('Failed to fetch network data, using mock:', err);
        return generateMockNetwork(centerId);
      }
    },
    enabled: !!centerId,
  });

  // Use networkData directly instead of separate relationshipsData
  const relationshipsData = networkData;

  // Generate mock network data for demo purposes
  const generateMockNetwork = (centerEntityId: number) => {
    const mockEntities: Entity[] = [
      { id: centerEntityId, entity_name: 'John Smith', entity_type: 'person', city: 'Houston', state: 'TX' },
      { id: 2, entity_name: 'Smith Holdings LLC', entity_type: 'company', city: 'Houston', state: 'TX' },
      { id: 3, entity_name: '123 Main Street', entity_type: 'property', address: '123 Main St', city: 'Houston', state: 'TX' },
      { id: 4, entity_name: 'Jane Doe', entity_type: 'person', city: 'Dallas', state: 'TX' },
      { id: 5, entity_name: 'First National Bank', entity_type: 'company', city: 'Houston', state: 'TX' },
      { id: 6, entity_name: '456 Oak Avenue', entity_type: 'property', address: '456 Oak Ave', city: 'Houston', state: 'TX' },
    ];

    const mockRelationships: Relationship[] = [
      { id: 1, entity1_id: centerEntityId, entity2_id: 2, relationship_type: 'owner', confidence_score: 0.95, role1: 'owner', role2: 'company' },
      { id: 2, entity1_id: centerEntityId, entity2_id: 3, relationship_type: 'owner', confidence_score: 0.9, role1: 'owner', role2: 'property' },
      { id: 3, entity1_id: 2, entity2_id: 3, relationship_type: 'owns', confidence_score: 0.85, role1: 'company', role2: 'property' },
      { id: 4, entity1_id: centerEntityId, entity2_id: 4, relationship_type: 'spouse', confidence_score: 0.98, role1: 'spouse', role2: 'spouse' },
      { id: 5, entity1_id: centerEntityId, entity2_id: 5, relationship_type: 'borrower', confidence_score: 0.92, role1: 'borrower', role2: 'lender' },
      { id: 6, entity1_id: 4, entity2_id: 6, relationship_type: 'owner', confidence_score: 0.88, role1: 'owner', role2: 'property' },
    ];

    return {
      entities: mockEntities,
      relationships: mockRelationships,
      center: mockEntities[0],
    };
  };

  // Initialize nodes with force-directed layout simulation
  useEffect(() => {
    const data = relationshipsData || (centerId ? generateMockNetwork(centerId) : null);
    if (!data) return;

    const { entities, relationships } = data;
    const centerX = width / 2;
    const centerY = height / 2;

    // Create nodes with initial positions
    const newNodes: NetworkNode[] = entities.map((entity: Entity, index: number) => {
      const angle = (2 * Math.PI * index) / entities.length;
      const radius = entity.id === centerId ? 0 : 150 + Math.random() * 50;
      return {
        id: entity.id,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        vx: 0,
        vy: 0,
        entity,
        isCenter: entity.id === centerId,
      };
    });

    // Create edges
    const newEdges: NetworkEdge[] = relationships.map((rel: Relationship) => ({
      source: rel.entity1_id,
      target: rel.entity2_id,
      relationship: rel,
    }));

    setNodes(newNodes);
    setEdges(newEdges);

    // Run force simulation
    runForceSimulation(newNodes, newEdges, centerX, centerY);
  }, [relationshipsData, centerId, width, height]);

  // Simple force-directed layout simulation
  const runForceSimulation = (
    nodeList: NetworkNode[],
    edgeList: NetworkEdge[],
    centerX: number,
    centerY: number
  ) => {
    const iterations = 100;
    const nodes = [...nodeList];

    for (let i = 0; i < iterations; i++) {
      // Repulsion between all nodes
      for (let j = 0; j < nodes.length; j++) {
        for (let k = j + 1; k < nodes.length; k++) {
          const dx = nodes[k].x - nodes[j].x;
          const dy = nodes[k].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 5000 / (dist * dist);

          nodes[j].vx -= (dx / dist) * force;
          nodes[j].vy -= (dy / dist) * force;
          nodes[k].vx += (dx / dist) * force;
          nodes[k].vy += (dy / dist) * force;
        }
      }

      // Attraction along edges
      for (const edge of edgeList) {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (!source || !target) continue;

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 150) * 0.01;

        source.vx += (dx / dist) * force;
        source.vy += (dy / dist) * force;
        target.vx -= (dx / dist) * force;
        target.vy -= (dy / dist) * force;
      }

      // Center gravity
      for (const node of nodes) {
        if (!node.isCenter) {
          node.vx += (centerX - node.x) * 0.001;
          node.vy += (centerY - node.y) * 0.001;
        }
      }

      // Apply velocities with damping
      for (const node of nodes) {
        if (!node.isCenter) {
          node.x += node.vx * 0.1;
          node.y += node.vy * 0.1;
          node.vx *= 0.9;
          node.vy *= 0.9;
        } else {
          node.x = centerX;
          node.y = centerY;
        }
      }
    }

    setNodes([...nodes]);
  };

  const handleNodeClick = (node: NetworkNode) => {
    setSelectedNode(node);
    onNodeClick?.(node.entity);
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 3));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.3));
  const handleReset = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  };

  const getEdgeThickness = (confidence: number) => 1 + confidence * 3;
  const getEdgeOpacity = (confidence: number) => 0.3 + confidence * 0.5;

  if (!centerId) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center', height }}>
        <Typography variant="h6" color="text.secondary">
          Select an entity to view its network
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Click on any person, company, or property to explore connections
        </Typography>
      </Paper>
    );
  }

  if (isLoading) {
    return (
      <Paper sx={{ p: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
        <CircularProgress />
      </Paper>
    );
  }

  return (
    <Paper sx={{ position: 'relative', overflow: 'hidden', height }}>
      {/* Controls */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 10,
          display: 'flex',
          gap: 1,
          backgroundColor: 'rgba(255,255,255,0.9)',
          borderRadius: 1,
          p: 0.5,
        }}
      >
        <Tooltip title="Zoom In">
          <IconButton size="small" onClick={handleZoomIn}>
            <ZoomInIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom Out">
          <IconButton size="small" onClick={handleZoomOut}>
            <ZoomOutIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Reset View">
          <IconButton size="small" onClick={handleReset}>
            <CenterFocusStrongIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Legend */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          zIndex: 10,
          backgroundColor: 'rgba(255,255,255,0.9)',
          borderRadius: 1,
          p: 1.5,
        }}
      >
        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1 }}>
          Entity Types
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            icon={<PersonIcon />}
            label="Person"
            size="small"
            sx={{ backgroundColor: `${entityColors.person}20`, color: entityColors.person }}
          />
          <Chip
            icon={<BusinessIcon />}
            label="Company"
            size="small"
            sx={{ backgroundColor: `${entityColors.company}20`, color: entityColors.company }}
          />
          <Chip
            icon={<HomeIcon />}
            label="Property"
            size="small"
            sx={{ backgroundColor: `${entityColors.property}20`, color: entityColors.property }}
          />
        </Box>
      </Box>

      {/* SVG Graph */}
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`${-offset.x} ${-offset.y} ${width} ${height}`}
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      >
        <g transform={`scale(${zoom})`}>
          {/* Edges */}
          {edges.map((edge) => {
            const sourceNode = nodes.find((n) => n.id === edge.source);
            const targetNode = nodes.find((n) => n.id === edge.target);
            if (!sourceNode || !targetNode) return null;

            const confidence = edge.relationship.confidence_score;

            return (
              <g key={edge.relationship.id}>
                <line
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke="#666"
                  strokeWidth={getEdgeThickness(confidence)}
                  strokeOpacity={getEdgeOpacity(confidence)}
                  strokeDasharray={confidence < 0.75 ? '5,5' : 'none'}
                  style={{ cursor: 'pointer' }}
                  onClick={() => onEdgeClick?.(edge.relationship)}
                />
                {/* Edge label */}
                <text
                  x={(sourceNode.x + targetNode.x) / 2}
                  y={(sourceNode.y + targetNode.y) / 2 - 5}
                  fontSize="10"
                  fill="#666"
                  textAnchor="middle"
                >
                  {edge.relationship.relationship_type}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const color = entityColors[node.entity.entity_type] || entityColors.person;
            const radius = node.isCenter ? 35 : 25;

            return (
              <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onClick={() => handleNodeClick(node)}
              >
                {/* Node circle */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={radius}
                  fill={color}
                  fillOpacity={0.2}
                  stroke={color}
                  strokeWidth={node.isCenter ? 3 : 2}
                />
                {/* Glow effect for center node */}
                {node.isCenter && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={radius + 5}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    strokeOpacity={0.3}
                  />
                )}
                {/* Node label */}
                <text
                  x={node.x}
                  y={node.y + radius + 15}
                  fontSize="11"
                  fill="#333"
                  textAnchor="middle"
                  fontWeight={node.isCenter ? 600 : 400}
                >
                  {node.entity.entity_name.length > 20
                    ? node.entity.entity_name.substring(0, 17) + '...'
                    : node.entity.entity_name}
                </text>
                {/* Entity type icon placeholder (using text for SVG) */}
                <text
                  x={node.x}
                  y={node.y + 5}
                  fontSize="16"
                  fill={color}
                  textAnchor="middle"
                >
                  {node.entity.entity_type === 'person' ? '👤' :
                    node.entity.entity_type === 'company' ? '🏢' : '🏠'}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Selected node info */}
      {selectedNode && (
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 10,
            backgroundColor: 'white',
            borderRadius: 2,
            p: 2,
            boxShadow: 2,
            maxWidth: 280,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <EntityIcon type={selectedNode.entity.entity_type} />
            <Typography variant="subtitle1" fontWeight={600}>
              {selectedNode.entity.entity_name}
            </Typography>
          </Box>
          <Chip
            label={selectedNode.entity.entity_type}
            size="small"
            sx={{
              backgroundColor: `${entityColors[selectedNode.entity.entity_type]}20`,
              color: entityColors[selectedNode.entity.entity_type],
              mb: 1,
            }}
          />
          {selectedNode.entity.city && selectedNode.entity.state && (
            <Typography variant="body2" color="text.secondary">
              {selectedNode.entity.city}, {selectedNode.entity.state}
            </Typography>
          )}
          <Button
            size="small"
            variant="outlined"
            sx={{ mt: 1 }}
            onClick={() => {
              // Navigate to entity detail or recenter graph
              if (onNodeClick) onNodeClick(selectedNode.entity);
            }}
          >
            View Details
          </Button>
        </Box>
      )}
    </Paper>
  );
};
