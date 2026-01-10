import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoginForm } from '../../src/components/auth/LoginForm';
import { AuthProvider } from '../../src/context/AuthContext';

// Mock the API service
jest.mock('../../src/services/api', () => ({
  apiService: {
    login: jest.fn(),
    getCurrentUser: jest.fn(),
  },
}));

// Create a wrapper with QueryClient and AuthProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
};

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

  it('renders login form correctly', () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    expect(screen.getByText('Welcome to DataGod')).toBeInTheDocument();
    expect(screen.getByText('Sign in to access your account')).toBeInTheDocument();
    // Use getByRole for more specific selection
    expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders forgot password link', () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
  });

  it('renders sign up link', () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
    expect(screen.getByText(/sign up/i)).toBeInTheDocument();
  });

  it('has required fields that prevent form submission when empty', () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    const emailInput = screen.getByRole('textbox', { name: /email/i });
    // Password field is type="password" so we need to find it differently
    const passwordInput = document.querySelector('input[type="password"]');

    // Both fields should be marked as required
    expect(emailInput).toBeRequired();
    expect(passwordInput).toHaveAttribute('required');
  });

  it('allows typing in email and password fields', () => {
    render(<LoginForm />, { wrapper: createWrapper() });

    const emailInput = screen.getByRole('textbox', { name: /email/i });
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement;

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(emailInput).toHaveValue('test@example.com');
    expect(passwordInput).toHaveValue('password123');
  });

  it('calls login API when form is submitted with valid credentials', async () => {
    const { apiService } = require('../../src/services/api');
    apiService.login.mockResolvedValue({
      data: { access_token: 'mock-token', token_type: 'bearer', expires_in: 3600 },
    });
    apiService.getCurrentUser.mockResolvedValue({
      data: { id: 1, username: 'test', email: 'test@example.com', roles: ['user'] },
    });

    render(<LoginForm />, { wrapper: createWrapper() });

    const emailInput = screen.getByRole('textbox', { name: /email/i });
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiService.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('shows error message on login failure', async () => {
    const { apiService } = require('../../src/services/api');
    apiService.login.mockRejectedValue({
      response: { data: { detail: 'Invalid credentials' } },
    });

    render(<LoginForm />, { wrapper: createWrapper() });

    const emailInput = screen.getByRole('textbox', { name: /email/i });
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('submit button shows loading state during login', async () => {
    const { apiService } = require('../../src/services/api');
    // Create a promise that we can control
    let resolveLogin: (value: any) => void;
    apiService.login.mockImplementation(() => new Promise((resolve) => {
      resolveLogin = resolve;
    }));

    render(<LoginForm />, { wrapper: createWrapper() });

    const emailInput = screen.getByRole('textbox', { name: /email/i });
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    // Button should show loading text
    await waitFor(() => {
      expect(screen.getByText(/signing in/i)).toBeInTheDocument();
    });

    // Resolve the promise to complete the test
    resolveLogin!({ data: { access_token: 'token', token_type: 'bearer', expires_in: 3600 } });
  });
});
