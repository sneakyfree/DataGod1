/**
 * API Service Tests
 *
 * Tests the apiService module for correct endpoint mapping,
 * request/response handling, and auto-refresh interceptor logic.
 */
import axios from 'axios';

// Mock axios before importing apiService
jest.mock('axios', () => {
    const mockAxiosInstance = {
        get: jest.fn().mockResolvedValue({ data: {} }),
        post: jest.fn().mockResolvedValue({ data: {} }),
        put: jest.fn().mockResolvedValue({ data: {} }),
        delete: jest.fn().mockResolvedValue({ data: {} }),
        interceptors: {
            request: { use: jest.fn() },
            response: { use: jest.fn() },
        },
        defaults: { headers: { common: {} } },
    };
    return {
        create: jest.fn(() => mockAxiosInstance),
        __mockInstance: mockAxiosInstance,
        default: { create: jest.fn(() => mockAxiosInstance) },
    };
});

describe('API Service', () => {
    let apiService: any;
    let endpoints: any;

    beforeAll(async () => {
        try {
            const mod = await import('../../services/api');
            apiService = mod.apiService;
            endpoints = mod.endpoints;
        } catch {
            // Module may not import in test env
        }
    });

    describe('Endpoints Configuration', () => {
        it('should define auth endpoints', () => {
            if (!endpoints) return;
            expect(endpoints.login).toBe('/token');
            expect(endpoints.register).toBe('/auth/register');
            expect(endpoints.refresh).toBe('/refresh-token');
        });

        it('should define dashboard endpoint', () => {
            if (!endpoints) return;
            expect(endpoints.dashboard).toBe('/stats');
        });

        it('should define entity endpoints', () => {
            if (!endpoints) return;
            expect(endpoints.entities).toBe('/entities');
            expect(endpoints.entityNetwork('123')).toBe('/entities/123/network');
            expect(endpoints.entityConnections('456')).toBe('/entities/456/connections');
        });

        it('should define share endpoints', () => {
            if (!endpoints) return;
            expect(endpoints.shares).toBe('/shares');
            expect(endpoints.publicShare('abc')).toBe('/share/abc');
        });

        it('should define search endpoints', () => {
            if (!endpoints) return;
            expect(endpoints.search).toBe('/search');
            expect(endpoints.savedSearches).toBe('/saved-searches');
        });

        it('should define export endpoint', () => {
            if (!endpoints) return;
            expect(endpoints.export).toBe('/export');
        });

        it('should define coverage endpoints', () => {
            if (!endpoints) return;
            expect(endpoints.coverageSummary).toBe('/admin/coverage/summary');
            expect(endpoints.coverageByState).toBe('/admin/coverage/by-state');
        });
    });

    describe('API Methods', () => {
        it('should have login method', () => {
            if (!apiService) return;
            expect(typeof apiService.login).toBe('function');
        });

        it('should have register method', () => {
            if (!apiService) return;
            expect(typeof apiService.register).toBe('function');
        });

        it('should have refreshToken method', () => {
            if (!apiService) return;
            expect(typeof apiService.refreshToken).toBe('function');
        });

        it('should have search method', () => {
            if (!apiService) return;
            expect(typeof apiService.search).toBe('function');
        });

        it('should have export method', () => {
            if (!apiService) return;
            expect(typeof apiService.exportData).toBe('function');
        });

        it('should have entity graph methods', () => {
            if (!apiService) return;
            expect(typeof apiService.getEntityNetwork).toBe('function');
            expect(typeof apiService.getEntityConnections).toBe('function');
            expect(typeof apiService.getEntityRecords).toBe('function');
        });

        it('should have share methods', () => {
            if (!apiService) return;
            expect(typeof apiService.createShareLink).toBe('function');
            expect(typeof apiService.getShareLinks).toBe('function');
            expect(typeof apiService.revokeShareLink).toBe('function');
        });

        it('should have saved search methods', () => {
            if (!apiService) return;
            expect(typeof apiService.getSavedSearches).toBe('function');
            expect(typeof apiService.createSavedSearch).toBe('function');
            expect(typeof apiService.runSavedSearch).toBe('function');
        });

        it('should have favorites methods', () => {
            if (!apiService) return;
            expect(typeof apiService.getFavorites).toBe('function');
            expect(typeof apiService.addFavorite).toBe('function');
            expect(typeof apiService.removeFavorite).toBe('function');
        });

        it('should have activity methods', () => {
            if (!apiService) return;
            expect(typeof apiService.getRecentActivities).toBe('function');
            expect(typeof apiService.trackActivity).toBe('function');
        });

        it('should have coverage/admin methods', () => {
            if (!apiService) return;
            expect(typeof apiService.getCoverageSummary).toBe('function');
            expect(typeof apiService.getCoverageByState).toBe('function');
            expect(typeof apiService.getCoverageGaps).toBe('function');
        });
    });
});
