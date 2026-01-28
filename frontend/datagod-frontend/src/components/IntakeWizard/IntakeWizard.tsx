'use client';

import React, { useState, useCallback } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Button,
    Stepper,
    Step,
    StepLabel,
    Alert,
    Chip,
    FormControlLabel,
    Checkbox,
    CircularProgress,
    FormHelperText,
    Divider,
} from '@mui/material';
import {
    Warning as WarningIcon,
    CheckCircle as CheckIcon,
    Error as ErrorIcon,
    HelpOutline as HelpIcon,
} from '@mui/icons-material';

interface Field {
    id: string;
    label: string;
    field_type: string;
    required?: boolean;
    help_text?: string;
    placeholder?: string;
    options?: { value: string; label: string }[];
    allow_uncertain?: boolean;
}

interface Group {
    id: string;
    label: string;
    order: number;
}

interface Validation {
    field_id: string;
    valid: boolean;
    severity: string;
    message: string;
}

interface Contradiction {
    fields: string[];
    description: string;
    options: string[];
}

interface VerificationTask {
    task_id: string;
    description: string;
    priority: string;
}

interface SessionData {
    session_id: string;
    schema_name: string;
    total_stages: number;
    current_stage: number;
    fields: Field[];
    groups: Group[];
}

interface IntakeWizardProps {
    schemaId?: string;
    onComplete?: (data: Record<string, any>) => void;
}

export function IntakeWizard({ schemaId = 'property_research', onComplete }: IntakeWizardProps) {
    const [session, setSession] = useState<SessionData | null>(null);
    const [formData, setFormData] = useState<Record<string, any>>({});
    const [uncertainFields, setUncertainFields] = useState<Set<string>>(new Set());
    const [validations, setValidations] = useState<Validation[]>([]);
    const [contradictions, setContradictions] = useState<Contradiction[]>([]);
    const [verificationTasks, setVerificationTasks] = useState<VerificationTask[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [complete, setComplete] = useState(false);

    // Start session
    const startSession = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/v2/intake/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ schema_id: schemaId }),
            });
            if (!response.ok) throw new Error('Failed to start session');
            const data = await response.json();
            setSession(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to start session');
        } finally {
            setLoading(false);
        }
    }, [schemaId]);

    // Submit current stage
    const submitStage = async () => {
        if (!session) return;
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/v2/intake/${session.session_id}/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: formData }),
            });
            if (!response.ok) throw new Error('Failed to submit stage');
            const result = await response.json();

            setValidations(result.validations || []);
            setContradictions(result.contradictions || []);
            setVerificationTasks(prev => [...prev, ...(result.verification_tasks || [])]);

            if (result.complete) {
                setComplete(true);
                onComplete?.(result.final_data);
            } else if (result.can_proceed && result.next_fields) {
                setSession(prev => prev ? {
                    ...prev,
                    current_stage: result.next_stage,
                    fields: result.next_fields,
                    groups: result.next_groups || prev.groups,
                } : null);
                setFormData({});
                setValidations([]);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to submit stage');
        } finally {
            setLoading(false);
        }
    };

    // Handle field change
    const handleFieldChange = (fieldId: string, value: any) => {
        setFormData(prev => ({ ...prev, [fieldId]: value }));
    };

    // Toggle uncertain flag
    const toggleUncertain = (fieldId: string) => {
        setUncertainFields(prev => {
            const next = new Set(prev);
            if (next.has(fieldId)) {
                next.delete(fieldId);
            } else {
                next.add(fieldId);
                setFormData(prev => ({ ...prev, [`${fieldId}_uncertain`]: true }));
            }
            return next;
        });
    };

    // Get validation for a field
    const getValidation = (fieldId: string) =>
        validations.find(v => v.field_id === fieldId);

    // Render a single field
    const renderField = (field: Field) => {
        const validation = getValidation(field.id);
        const hasError = validation && !validation.valid && validation.severity === 'error';
        const isUncertain = uncertainFields.has(field.id);

        return (
            <Box key={field.id} sx={{ mb: 3 }}>
                {field.field_type === 'select' ? (
                    <FormControl fullWidth error={hasError}>
                        <InputLabel>{field.label}</InputLabel>
                        <Select
                            value={formData[field.id] || ''}
                            onChange={(e) => handleFieldChange(field.id, e.target.value)}
                            label={field.label}
                            disabled={isUncertain}
                        >
                            {field.options?.map(opt => (
                                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                            ))}
                        </Select>
                        {hasError && <FormHelperText>{validation.message}</FormHelperText>}
                    </FormControl>
                ) : field.field_type === 'boolean' ? (
                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={formData[field.id] || false}
                                onChange={(e) => handleFieldChange(field.id, e.target.checked)}
                            />
                        }
                        label={field.label}
                    />
                ) : field.field_type === 'multi_select' ? (
                    <FormControl fullWidth error={hasError}>
                        <InputLabel>{field.label}</InputLabel>
                        <Select
                            multiple
                            value={formData[field.id] || []}
                            onChange={(e) => handleFieldChange(field.id, e.target.value)}
                            label={field.label}
                            renderValue={(selected) => (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                    {(selected as string[]).map(value => (
                                        <Chip key={value} label={field.options?.find(o => o.value === value)?.label || value} size="small" />
                                    ))}
                                </Box>
                            )}
                        >
                            {field.options?.map(opt => (
                                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                ) : (
                    <TextField
                        fullWidth
                        label={field.label}
                        value={formData[field.id] || ''}
                        onChange={(e) => handleFieldChange(field.id, e.target.value)}
                        placeholder={field.placeholder}
                        error={hasError}
                        helperText={hasError ? validation.message : field.help_text}
                        disabled={isUncertain}
                        required={field.required}
                        type={field.field_type === 'number' || field.field_type === 'currency' ? 'number' : 'text'}
                    />
                )}

                {field.allow_uncertain && (
                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={isUncertain}
                                onChange={() => toggleUncertain(field.id)}
                                size="small"
                            />
                        }
                        label={<Typography variant="caption" color="text.secondary">I'm not sure</Typography>}
                        sx={{ mt: 0.5 }}
                    />
                )}
            </Box>
        );
    };

    // Render start screen
    if (!session && !complete) {
        return (
            <Card sx={{ maxWidth: 600, mx: 'auto', mt: 4 }}>
                <CardContent sx={{ textAlign: 'center', py: 4 }}>
                    <Typography variant="h5" gutterBottom>Property Research Intake</Typography>
                    <Typography color="text.secondary" sx={{ mb: 3 }}>
                        Answer a few questions to help us research your property.
                    </Typography>
                    <Button variant="contained" onClick={startSession} disabled={loading}>
                        {loading ? <CircularProgress size={24} /> : 'Get Started'}
                    </Button>
                    {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
                </CardContent>
            </Card>
        );
    }

    // Render completion screen
    if (complete) {
        return (
            <Card sx={{ maxWidth: 600, mx: 'auto', mt: 4 }}>
                <CardContent sx={{ textAlign: 'center', py: 4 }}>
                    <CheckIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
                    <Typography variant="h5" gutterBottom>Intake Complete!</Typography>
                    <Typography color="text.secondary">
                        Your information has been collected. We'll begin the research process.
                    </Typography>
                    {verificationTasks.length > 0 && (
                        <Box sx={{ mt: 3, textAlign: 'left' }}>
                            <Typography variant="subtitle2" gutterBottom>Verification Tasks:</Typography>
                            {verificationTasks.map(task => (
                                <Alert key={task.task_id} severity="info" sx={{ mb: 1 }}>
                                    {task.description}
                                </Alert>
                            ))}
                        </Box>
                    )}
                </CardContent>
            </Card>
        );
    }

    // Render wizard form
    return (
        <Card sx={{ maxWidth: 700, mx: 'auto', mt: 4 }}>
            <CardContent>
                {/* Stepper */}
                <Stepper activeStep={(session?.current_stage || 1) - 1} sx={{ mb: 4 }}>
                    {Array.from({ length: session?.total_stages || 4 }, (_, i) => (
                        <Step key={i}>
                            <StepLabel>Stage {i + 1}</StepLabel>
                        </Step>
                    ))}
                </Stepper>

                {/* Current stage title */}
                <Typography variant="h6" gutterBottom>
                    {session?.groups?.[0]?.label || `Stage ${session?.current_stage}`}
                </Typography>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                {/* Contradictions */}
                {contradictions.map((c, i) => (
                    <Alert key={i} severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>
                        <Typography variant="subtitle2">Contradiction Detected</Typography>
                        <Typography variant="body2">{c.description}</Typography>
                    </Alert>
                ))}

                {/* Fields */}
                <Divider sx={{ my: 2 }} />
                {session?.fields?.map(renderField)}

                {/* Actions */}
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
                    <Button
                        variant="contained"
                        onClick={submitStage}
                        disabled={loading}
                    >
                        {loading ? <CircularProgress size={24} /> : 'Continue'}
                    </Button>
                </Box>
            </CardContent>
        </Card>
    );
}

export default IntakeWizard;
