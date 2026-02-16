'use client';

import { useState } from 'react';
import {
    Box,
    Typography,
    Container,
    Paper,
    Tabs,
    Tab,
    Card,
    CardContent,
    Alert,
    Chip,
    Grid,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
} from '@mui/material';
import {
    Visibility,
    Code,
    GavelRounded,
    Shield,
    ExpandMore,
    CheckCircle,
    Info,
    AccountTree,
} from '@mui/icons-material';
import { ProtectedRoute } from '../../context/AuthContext';
import { featureFlag } from '../../config/featureFlags';

interface TabPanelProps {
    children?: React.ReactNode;
    value: number;
    index: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
    return value === index ? <Box sx={{ pt: 3 }}>{children}</Box> : null;
}

const LAYERS = [
    {
        id: 'user',
        label: 'User View',
        icon: <Visibility />,
        color: '#1976d2',
        description: 'Plain English explanations for end users',
        examples: [
            'Our system detected an unusual pattern in the data',
            'We are 87% confident this is a real anomaly',
            'Review the flagged records and verify the data is correct',
        ],
    },
    {
        id: 'technical',
        label: 'Technical',
        icon: <Code />,
        color: '#9c27b0',
        description: 'Feature importance, model details, and method information',
        examples: [
            'Detection method: Statistical (Z-Score > 3.0)',
            'Contributing features: amount_deviation=4.2, frequency_score=0.89',
            'Model version: v1.0, trained on 50,000 records',
        ],
    },
    {
        id: 'audit',
        label: 'Audit Trail',
        icon: <GavelRounded />,
        color: '#ed6c02',
        description: 'Complete decision chain and input/output trace',
        examples: [
            'Input features at decision point with exact values',
            'Threshold used: 0.70, Decision: FLAGGED',
            'Full processing chain with timestamps',
        ],
    },
    {
        id: 'compliance',
        label: 'Compliance',
        icon: <Shield />,
        color: '#2e7d32',
        description: 'Regulatory documentation, bias assessment, and data governance',
        examples: [
            'Data handling compliant with retention policy',
            'Model bias assessment completed across jurisdictions',
            'Records retained for 7 years per data retention policy',
        ],
    },
];

function ExplainabilityContent() {
    const [activeLayer, setActiveLayer] = useState(0);

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ mb: 4 }}>
                <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AccountTree color="primary" /> Explainability
                </Typography>
                <Typography variant="body1" color="text.secondary">
                    DataGod uses a 4-layer explainability framework to make every AI decision transparent and auditable
                </Typography>
            </Box>

            <Alert severity="info" sx={{ mb: 3 }}>
                Select an explainability layer below to see what information is available at each level
            </Alert>

            {/* Layer Selector */}
            <Paper sx={{ mb: 4 }}>
                <Tabs
                    value={activeLayer}
                    onChange={(_, v) => setActiveLayer(v)}
                    variant="fullWidth"
                    sx={{ borderBottom: 1, borderColor: 'divider' }}
                >
                    {LAYERS.map((layer) => (
                        <Tab
                            key={layer.id}
                            icon={layer.icon}
                            label={layer.label}
                            sx={{ minHeight: 72 }}
                        />
                    ))}
                </Tabs>

                {LAYERS.map((layer, idx) => (
                    <TabPanel key={layer.id} value={activeLayer} index={idx}>
                        <Box sx={{ p: 3 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                                <Box sx={{ color: layer.color, display: 'flex' }}>{layer.icon}</Box>
                                <Box>
                                    <Typography variant="h6">{layer.label}</Typography>
                                    <Typography variant="body2" color="text.secondary">{layer.description}</Typography>
                                </Box>
                            </Box>

                            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                                Example outputs:
                            </Typography>
                            <List dense>
                                {layer.examples.map((example, i) => (
                                    <ListItem key={i}>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <CheckCircle fontSize="small" color="success" />
                                        </ListItemIcon>
                                        <ListItemText primary={example} />
                                    </ListItem>
                                ))}
                            </List>
                        </Box>
                    </TabPanel>
                ))}
            </Paper>

            {/* Supported Decision Types */}
            <Typography variant="h5" gutterBottom>
                Supported Decision Types
            </Typography>
            <Grid container spacing={2}>
                {[
                    { title: 'Anomaly Detection', desc: 'Why a record was flagged as anomalous', chipColor: 'error' as const },
                    { title: 'Search Ranking', desc: 'How search results are ordered and filtered', chipColor: 'primary' as const },
                    { title: 'Data Quality', desc: 'Quality score methodology and issue identification', chipColor: 'warning' as const },
                    { title: 'Entity Resolution', desc: 'How entities are linked across data sources', chipColor: 'success' as const },
                ].map((type) => (
                    <Grid item xs={12} sm={6} key={type.title}>
                        <Card variant="outlined">
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                                    <Typography variant="subtitle1" fontWeight={600}>{type.title}</Typography>
                                    <Chip label="Active" size="small" color={type.chipColor} />
                                </Box>
                                <Typography variant="body2" color="text.secondary">{type.desc}</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* FAQ */}
            <Box sx={{ mt: 4 }}>
                <Typography variant="h5" gutterBottom>Frequently Asked Questions</Typography>
                {[
                    {
                        q: 'How does explainability work?',
                        a: 'Every AI decision in DataGod is recorded with a structured explanation. The 4-layer format ensures the right level of detail for each audience—from plain English summaries for users to full audit trails for compliance.',
                    },
                    {
                        q: 'Can I export explanation data?',
                        a: 'Yes. Audit and compliance layers are included in exported reports. You can also access explanations via the API for integration with your compliance tools.',
                    },
                    {
                        q: 'Is explanation data retained?',
                        a: 'Explanation records are retained per your data retention policy (default: 7 years for audit-grade records).',
                    },
                ].map((faq, idx) => (
                    <Accordion key={idx} variant="outlined">
                        <AccordionSummary expandIcon={<ExpandMore />}>
                            <Typography fontWeight={500}>{faq.q}</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                            <Typography variant="body2" color="text.secondary">{faq.a}</Typography>
                        </AccordionDetails>
                    </Accordion>
                ))}
            </Box>
        </Container>
    );
}

export default function ExplainabilityPage() {
    if (!featureFlag('explainability')) {
        return (
            <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
                <Typography variant="h5" color="text.secondary">
                    Explainability Dashboard is coming soon
                </Typography>
            </Container>
        );
    }

    return (
        <ProtectedRoute>
            <ExplainabilityContent />
        </ProtectedRoute>
    );
}
