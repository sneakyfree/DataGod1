'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { apiService } from '../services/api';

// Types
export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  roles: string[];
  subscription_tier: 'free' | 'basic' | 'pro' | 'enterprise';
  disabled: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  register: (data: RegisterData) => Promise<void>;
  refreshToken: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  confirmResetPassword: (token: string, newPassword: string) => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = 'access_token';
const USER_KEY = 'user_data';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = () => {
      try {
        const storedToken = localStorage.getItem(TOKEN_KEY);
        const storedUser = localStorage.getItem(USER_KEY);

        if (storedToken && storedUser) {
          const user = JSON.parse(storedUser) as User;
          setState({
            user,
            token: storedToken,
            isLoading: false,
            isAuthenticated: true,
            error: null,
          });
        } else {
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    initializeAuth();
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // The API expects username, but we use email for login
      const response = await apiService.login({
        email: credentials.email,
        password: credentials.password,
      });

      const { access_token } = response.data;

      // Store token
      localStorage.setItem(TOKEN_KEY, access_token);

      // Fetch user data
      const userResponse = await apiService.getCurrentUser();
      const user = userResponse.data as User;

      // Store user data
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      setState({
        user,
        token: access_token,
        isLoading: false,
        isAuthenticated: true,
        error: null,
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed. Please check your credentials.';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, []);

  const register = useCallback(async (data: RegisterData) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiService.register({
        username: data.username,
        email: data.email,
        password: data.password,
        full_name: data.full_name,
      });

      // If registration returns a token, log the user in
      if (response.data.access_token) {
        const { access_token } = response.data;
        localStorage.setItem(TOKEN_KEY, access_token);

        // Fetch user data
        const userResponse = await apiService.getCurrentUser();
        const user = userResponse.data as User;
        localStorage.setItem(USER_KEY, JSON.stringify(user));

        setState({
          user,
          token: access_token,
          isLoading: false,
          isAuthenticated: true,
          error: null,
        });
      } else {
        // Registration successful but no auto-login
        setState(prev => ({ ...prev, isLoading: false }));
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Registration failed. Please try again.';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setState({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,
    });
  }, []);

  const refreshToken = useCallback(async () => {
    try {
      const response = await apiService.refreshToken();
      const { access_token } = response.data;
      localStorage.setItem(TOKEN_KEY, access_token);
      setState(prev => ({ ...prev, token: access_token }));
    } catch (error) {
      // If refresh fails, log out
      logout();
      throw error;
    }
  }, [logout]);

  const resetPassword = useCallback(async (email: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await apiService.forgotPassword(email);
      setState(prev => ({ ...prev, isLoading: false }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to send reset email.';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, []);

  const confirmResetPassword = useCallback(async (token: string, newPassword: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await apiService.resetPassword(token, newPassword);
      setState(prev => ({ ...prev, isLoading: false }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to reset password.';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, []);

  const updateProfile = useCallback(async (data: Partial<User>) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiService.updateProfile(data);
      const updatedUser = response.data as User;

      localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));

      setState(prev => ({
        ...prev,
        user: updatedUser,
        isLoading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to update profile.';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const value: AuthContextValue = {
    ...state,
    login,
    logout,
    register,
    refreshToken,
    resetPassword,
    confirmResetPassword,
    updateProfile,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Protected Route Component
interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoles?: string[];
}

export function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    return null;
  }

  if (requiredRoles && user) {
    const hasRequiredRole = requiredRoles.some(role => user.roles.includes(role));
    if (!hasRequiredRole) {
      // Redirect to unauthorized or dashboard
      if (typeof window !== 'undefined') {
        window.location.href = '/dashboard';
      }
      return null;
    }
  }

  return <>{children}</>;
}
