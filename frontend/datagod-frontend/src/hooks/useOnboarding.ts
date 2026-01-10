'use client';

import { useState, useEffect, useCallback } from 'react';

const ONBOARDING_STORAGE_KEY = 'datagod_onboarding';

interface OnboardingState {
  hasSeenWelcome: boolean;
  hasCompletedTour: boolean;
  hasDismissedQuickStart: boolean;
  completedSteps: string[];
  lastVisit: string | null;
}

const defaultState: OnboardingState = {
  hasSeenWelcome: false,
  hasCompletedTour: false,
  hasDismissedQuickStart: false,
  completedSteps: [],
  lastVisit: null,
};

export const useOnboarding = () => {
  const [state, setState] = useState<OnboardingState>(defaultState);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load state from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(ONBOARDING_STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          setState({ ...defaultState, ...parsed });
        }
      } catch (e) {
        console.warn('Failed to load onboarding state:', e);
      }
      setIsLoaded(true);
    }
  }, []);

  // Save state to localStorage whenever it changes
  useEffect(() => {
    if (isLoaded && typeof window !== 'undefined') {
      try {
        localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(state));
      } catch (e) {
        console.warn('Failed to save onboarding state:', e);
      }
    }
  }, [state, isLoaded]);

  const markWelcomeSeen = useCallback(() => {
    setState((prev) => ({ ...prev, hasSeenWelcome: true }));
  }, []);

  const markTourCompleted = useCallback(() => {
    setState((prev) => ({ ...prev, hasCompletedTour: true }));
  }, []);

  const dismissQuickStart = useCallback(() => {
    setState((prev) => ({ ...prev, hasDismissedQuickStart: true }));
  }, []);

  const completeStep = useCallback((stepId: string) => {
    setState((prev) => ({
      ...prev,
      completedSteps: prev.completedSteps.includes(stepId)
        ? prev.completedSteps
        : [...prev.completedSteps, stepId],
    }));
  }, []);

  const isStepCompleted = useCallback(
    (stepId: string) => state.completedSteps.includes(stepId),
    [state.completedSteps]
  );

  const resetOnboarding = useCallback(() => {
    setState(defaultState);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(ONBOARDING_STORAGE_KEY);
    }
  }, []);

  const updateLastVisit = useCallback(() => {
    setState((prev) => ({ ...prev, lastVisit: new Date().toISOString() }));
  }, []);

  // Check if this is a first-time user
  const isFirstTimeUser = !state.hasSeenWelcome && isLoaded;

  // Check if quick start should be shown
  const shouldShowQuickStart =
    isLoaded && !state.hasDismissedQuickStart && !state.hasCompletedTour;

  // Check if tour should be shown
  const shouldShowTour = isLoaded && state.hasSeenWelcome && !state.hasCompletedTour;

  return {
    state,
    isLoaded,
    isFirstTimeUser,
    shouldShowQuickStart,
    shouldShowTour,
    markWelcomeSeen,
    markTourCompleted,
    dismissQuickStart,
    completeStep,
    isStepCompleted,
    resetOnboarding,
    updateLastVisit,
  };
};
