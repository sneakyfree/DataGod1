'use client';

import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Container,
    Paper,
    Stepper,
    Step,
    StepLabel,
    StepContent,
    Button,
    TextField,
    FormGroup,
    FormControlLabel,
    Checkbox,
    Alert,
    Chip,
    Grid,
    Card,
    CardContent,
    CardActionArea,
} from '@mui/material';
import {
    Person,
    Search,
    NotificationsActive,
    Tune,
    CheckCircle,
    Business,
    Home,
    AccountBalance,
    Gavel,
} from '@mui/icons-material';

interface OnboardingWizardProps {
    onComplete: () => void;
    userName?: string;
}

const RECORD_TYPES = [
    { id: 'business_filing', label: 'Business Filings', icon: <Business /> },
    { id: 'ucc', label: 'UCC Filings', icon: <Gavel /> },
    { id: 'property', label: 'Property Records', icon: <Home /> },
    { id: 'court', label: 'Court Records', icon: <AccountBalance /> },
];

export default function OnboardingWizard({ onComplete, userName }: OnboardingWizardProps) {
    const [activeStep, setActiveStep] = useState(0);
    const [profile, setProfile] = useState({
        displayName: userName || '',
        organization: '',
        role: '',
    });
    const [interests, setInterests] = useState<string[]>([]);
    const [preferences, setPreferences] = useState({
        emailAlerts: true,
        weeklyDigest: true,
        anomalyAlerts: true,
    });
    const [isCompleting, setIsCompleting] = useState(false);

    const toggleInterest = (id: string) => {
        setInterests((prev) =>
            prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
        );
    };

    const handleComplete = () => {
        setIsCompleting(true);
        // Persist onboarding preferences
        try {
            localStorage.setItem('datagod_onboarding_complete', 'true');
            localStorage.setItem('datagod_onboarding_data', JSON.stringify({
                profile,
                interests,
                preferences,
                completedAt: new Date().toISOString(),
            }));
        } catch { }
        setTimeout(() => {
            onComplete();
        }, 800);
    };

    const steps = [
        {
            label: 'Welcome',
            icon: <Person />,
            content: (
                <Box>
                    <Typography variant="body1" gutterBottom>
                        Welcome to DataGod! Let&apos;s set up your profile so we can personalize your experience.
                    </Typography>
                    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <TextField
                            label="Display Name"
                            value={profile.displayName}
                            onChange={(e) => setProfile({ ...profile, displayName: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label="Organization (optional)"
                            value={profile.organization}
                            onChange={(e) => setProfile({ ...profile, organization: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label="Your Role (e.g., Analyst, Researcher)"
                            value={profile.role}
                            onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                            fullWidth
                        />
                    </Box>
                </Box>
            ),
        },
        {
            label: 'Interests',
            icon: <Search />,
            content: (
                <Box>
                    <Typography variant="body1" gutterBottom>
                        What types of records are you most interested in? We&apos;ll prioritize these in your dashboards.
                    </Typography>
                    <Grid container spacing={2} sx={{ mt: 1 }}>
                        {RECORD_TYPES.map((type) => (
                            <Grid item xs={6} key={type.id}>
                                <Card
                                    variant="outlined"
                                    sx={{
                                        borderColor: interests.includes(type.id) ? 'primary.main' : 'divider',
                                        borderWidth: interests.includes(type.id) ? 2 : 1,
                                        transition: '0.2s',
                                    }}
                                >
                                    <CardActionArea onClick={() => toggleInterest(type.id)}>
                                        <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                            <Box sx={{ color: interests.includes(type.id) ? 'primary.main' : 'text.secondary' }}>
                                                {type.icon}
                                            </Box>
                                            <Typography variant="body2" fontWeight={500}>{type.label}</Typography>
                                            {interests.includes(type.id) && (
                                                <CheckCircle color="primary" fontSize="small" sx={{ ml: 'auto' }} />
                                            )}
                                        </CardContent>
                                    </CardActionArea>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            ),
        },
        {
            label: 'Notifications',
            icon: <NotificationsActive />,
            content: (
                <Box>
                    <Typography variant="body1" gutterBottom>
                        Stay informed about changes and anomalies in the data you care about.
                    </Typography>
                    <FormGroup sx={{ mt: 2 }}>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={preferences.emailAlerts}
                                    onChange={(e) => setPreferences({ ...preferences, emailAlerts: e.target.checked })}
                                />
                            }
                            label="Email alerts for new records matching saved searches"
                        />
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={preferences.weeklyDigest}
                                    onChange={(e) => setPreferences({ ...preferences, weeklyDigest: e.target.checked })}
                                />
                            }
                            label="Weekly digest of platform updates"
                        />
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={preferences.anomalyAlerts}
                                    onChange={(e) => setPreferences({ ...preferences, anomalyAlerts: e.target.checked })}
                                />
                            }
                            label="Real-time anomaly detection alerts"
                        />
                    </FormGroup>
                </Box>
            ),
        },
        {
            label: 'All Set!',
            icon: <Tune />,
            content: (
                <Box>
                    <Alert severity="success" sx={{ mb: 2 }}>
                        Your account is ready to go!
                    </Alert>
                    <Typography variant="body1" gutterBottom>
                        Here&apos;s a summary of your setup:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                        {profile.displayName && <Chip label={`Name: ${profile.displayName}`} variant="outlined" />}
                        {profile.organization && <Chip label={`Org: ${profile.organization}`} variant="outlined" />}
                        {interests.map((i) => (
                            <Chip key={i} label={i.replace(/_/g, ' ')} color="primary" size="small" sx={{ textTransform: 'capitalize' }} />
                        ))}
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                        You can change any of these settings later from the Settings page.
                    </Typography>
                </Box>
            ),
        },
    ];

    return (
        <Container maxWidth="sm" sx={{ py: 4 }}>
            <Paper sx={{ p: 4 }}>
                <Typography variant="h4" gutterBottom fontWeight={600}>
                    Getting Started
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                    Complete these steps to personalize your DataGod experience
                </Typography>

                <Stepper activeStep={activeStep} orientation="vertical" sx={{ mt: 3 }}>
                    {steps.map((step, index) => (
                        <Step key={step.label}>
                            <StepLabel icon={step.icon}>{step.label}</StepLabel>
                            <StepContent>
                                {step.content}
                                <Box sx={{ mt: 3, display: 'flex', gap: 1 }}>
                                    {index > 0 && (
                                        <Button onClick={() => setActiveStep(index - 1)}>
                                            Back
                                        </Button>
                                    )}
                                    {index < steps.length - 1 ? (
                                        <Button
                                            variant="contained"
                                            onClick={() => setActiveStep(index + 1)}
                                        >
                                            Continue
                                        </Button>
                                    ) : (
                                        <Button
                                            variant="contained"
                                            color="success"
                                            onClick={handleComplete}
                                            disabled={isCompleting}
                                        >
                                            {isCompleting ? 'Setting up...' : 'Get Started'}
                                        </Button>
                                    )}
                                </Box>
                            </StepContent>
                        </Step>
                    ))}
                </Stepper>
            </Paper>
        </Container>
    );
}
