import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardStats } from '../../src/components/DashboardStats';

// Mock the API service
jest.mock('../../src/services/api', () => ({
  apiService: {
    getDashboardStats: jest.fn(),
  },
}));

// Create a wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('DashboardStats', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    const { apiService } = require('../../src/services/api');
    // Return a pending promise to simulate loading
    apiService.getDashboardStats.mockImplementation(() => new Promise(() => {}));

    render(<DashboardStats />, { wrapper: createWrapper() });

    // The component should render even during loading
    await waitFor(() => {
      expect(screen.getByText(/total records/i)).toBeInTheDocument();
    });
  });

  it('displays stats when data is loaded', async () => {
    const { apiService } = require('../../src/services/api');
    apiService.getDashboardStats.mockResolvedValue({
      data: {
        totalRecords: 15000,
        jurisdictions: 50,
        dataSources: 25,
        activeScrapers: 10,
      },
    });

    render(<DashboardStats />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('15,000')).toBeInTheDocument();
    });

    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders all stat labels', async () => {
    const { apiService } = require('../../src/services/api');
    apiService.getDashboardStats.mockResolvedValue({
      data: {
        totalRecords: 100,
        jurisdictions: 10,
        dataSources: 5,
        activeScrapers: 2,
      },
    });

    render(<DashboardStats />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/total records/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/jurisdictions/i)).toBeInTheDocument();
    expect(screen.getByText(/data sources/i)).toBeInTheDocument();
    expect(screen.getByText(/active scrapers/i)).toBeInTheDocument();
  });

  it('calls the API on mount', async () => {
    const { apiService } = require('../../src/services/api');
    apiService.getDashboardStats.mockResolvedValue({
      data: {
        totalRecords: 0,
        jurisdictions: 0,
        dataSources: 0,
        activeScrapers: 0,
      },
    });

    render(<DashboardStats />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(apiService.getDashboardStats).toHaveBeenCalled();
    });
  });

  it('displays formatted numbers with thousand separators', async () => {
    const { apiService } = require('../../src/services/api');
    apiService.getDashboardStats.mockResolvedValue({
      data: {
        totalRecords: 1234567,
        jurisdictions: 1000,
        dataSources: 100,
        activeScrapers: 50,
      },
    });

    render(<DashboardStats />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('1,234,567')).toBeInTheDocument();
    });

    expect(screen.getByText('1,000')).toBeInTheDocument();
  });
});
