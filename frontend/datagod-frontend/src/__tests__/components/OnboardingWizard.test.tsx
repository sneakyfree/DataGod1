/**
 * OnboardingWizard Component Tests
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

describe('OnboardingWizard', () => {
    let OnboardingWizard: any;

    beforeAll(async () => {
        try {
            const mod = await import('../../components/onboarding/OnboardingWizard');
            OnboardingWizard = mod.default;
        } catch {
            // Component may not be importable
        }
    });

    // localStorage mock is global from jest.setup.js

    it('should be importable', () => {
        expect(OnboardingWizard).toBeDefined();
    });

    it('should render Getting Started heading', () => {
        if (!OnboardingWizard) return;
        render(<OnboardingWizard onComplete={jest.fn()} />);
        expect(screen.getByText('Getting Started')).toBeInTheDocument();
    });

    it('should render the Welcome step label', () => {
        if (!OnboardingWizard) return;
        render(<OnboardingWizard onComplete={jest.fn()} />);
        expect(screen.getByText('Welcome')).toBeInTheDocument();
    });

    it('should render Continue button on first step', () => {
        if (!OnboardingWizard) return;
        render(<OnboardingWizard onComplete={jest.fn()} />);
        expect(screen.getByText('Continue')).toBeInTheDocument();
    });

    it('should advance to Interests step on Continue', async () => {
        if (!OnboardingWizard) return;
        render(<OnboardingWizard onComplete={jest.fn()} />);
        fireEvent.click(screen.getByText('Continue'));
        await waitFor(() => {
            expect(screen.getByText(/types of records/i)).toBeInTheDocument();
        });
    });

    it('should show Display Name field on Welcome step', () => {
        if (!OnboardingWizard) return;
        render(<OnboardingWizard onComplete={jest.fn()} />);
        expect(screen.getByLabelText('Display Name')).toBeInTheDocument();
    });

    it('should accept userName prop for Display Name', () => {
        if (!OnboardingWizard) return;
        render(<OnboardingWizard onComplete={jest.fn()} userName="TestUser" />);
        const field = screen.getByLabelText('Display Name') as HTMLInputElement;
        expect(field.value).toBe('TestUser');
    });
});
