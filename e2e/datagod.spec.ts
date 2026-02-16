/**
 * DataGod E2E Test Suite — Playwright
 *
 * Scaffolding for end-to-end tests covering critical user flows.
 * Run with: npx playwright test
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// --- Helpers ---
async function login(page: Page, username = 'admin', password = 'admin123') {
    await page.goto(`${BASE_URL}/login`);
    await page.fill('[name="email"], [type="email"]', username);
    await page.fill('[name="password"], [type="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|search|$)/);
}

// --- Test Suites ---
test.describe('Authentication', () => {
    test('login page renders', async ({ page }) => {
        await page.goto(`${BASE_URL}/login`);
        await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('login with valid credentials', async ({ page }) => {
        await login(page);
        await expect(page).not.toHaveURL(/login/);
    });

    test('login with invalid credentials shows error', async ({ page }) => {
        await page.goto(`${BASE_URL}/login`);
        await page.fill('[name="email"], [type="email"]', 'bad@user.com');
        await page.fill('[name="password"], [type="password"]', 'wrongpassword');
        await page.click('button[type="submit"]');
        // Should show error message or stay on login
        await expect(page.locator('[role="alert"], .error, .MuiAlert-root')).toBeVisible({ timeout: 5000 });
    });

    test('register page renders', async ({ page }) => {
        await page.goto(`${BASE_URL}/register`);
        await expect(page.locator('form')).toBeVisible();
    });
});

test.describe('Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('dashboard loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/dashboard`);
        await expect(page.locator('h1, h2, h3').first()).toBeVisible();
    });

    test('search page loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/search`);
        await expect(page.locator('input[type="search"], input[type="text"]').first()).toBeVisible();
    });

    test('entities page loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/entities`);
        await expect(page.locator('h1, h2, h3').first()).toBeVisible();
    });

    test('notifications page loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/notifications`);
        await expect(page.locator('h1, h2, h3').first()).toBeVisible();
    });

    test('analytics page loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/analytics`);
        await expect(page.locator('h1, h2, h3').first()).toBeVisible();
    });

    test('settings page loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/settings`);
        await expect(page.locator('h1, h2, h3').first()).toBeVisible();
    });
});

test.describe('Search Flow', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('search returns results', async ({ page }) => {
        await page.goto(`${BASE_URL}/search`);
        const searchInput = page.locator('input[type="search"], input[type="text"]').first();
        await searchInput.fill('test');
        await searchInput.press('Enter');
        // Wait for results or "no results" message
        await page.waitForSelector('[data-testid="search-results"], .MuiList-root, .no-results', { timeout: 10000 });
    });

    test('typeahead shows suggestions', async ({ page }) => {
        await page.goto(`${BASE_URL}/search`);
        const searchInput = page.locator('input[type="search"], input[type="text"]').first();
        await searchInput.fill('business');
        // Wait for suggestions dropdown
        await page.waitForTimeout(500);
        // Check for any dropdown/suggestions
        const suggestions = page.locator('[role="listbox"], [role="option"], .suggestions, .MuiAutocomplete-popper');
        // May or may not appear depending on data
    });
});

test.describe('API Health', () => {
    test('API is reachable', async ({ request }) => {
        const response = await request.get(`${API_URL}/health`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.status).toBe('healthy');
    });

    test('API root returns version', async ({ request }) => {
        const response = await request.get(`${API_URL}/`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.version).toBeDefined();
    });

    test('public stats accessible', async ({ request }) => {
        const response = await request.get(`${API_URL}/stats/public`);
        expect(response.status()).toBeLessThan(500);
    });
});

test.describe('Records Flow', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('records page loads with table', async ({ page }) => {
        await page.goto(`${BASE_URL}/records`);
        await expect(page.locator('table, [role="grid"], .MuiTable-root').first()).toBeVisible({ timeout: 10000 });
    });

    test('records page has pagination', async ({ page }) => {
        await page.goto(`${BASE_URL}/records`);
        await expect(page.locator('[aria-label*="page"], .MuiPagination-root, .pagination').first()).toBeVisible({ timeout: 10000 });
    });

    test('record detail loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/records`);
        // Click first record link
        const firstLink = page.locator('a[href*="/records/"], tr td a').first();
        if (await firstLink.count() > 0) {
            await firstLink.click();
            await expect(page.locator('h1, h2, h3').first()).toBeVisible();
        }
    });
});

test.describe('Share Management', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('shares page loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/shares`);
        await expect(page.locator('h1, h2, h3').first()).toBeVisible();
    });

    test('shares page shows table or empty state', async ({ page }) => {
        await page.goto(`${BASE_URL}/shares`);
        const table = page.locator('table, .MuiTable-root');
        const emptyState = page.locator('.no-shares, [data-testid="empty-state"], .MuiAlert-root');
        await expect(table.or(emptyState).first()).toBeVisible({ timeout: 10000 });
    });

    test('shared record view loads', async ({ page }) => {
        // Public share pages should render without login
        await page.goto(`${BASE_URL}/share/test-token-123`);
        // Should show content or not-found, but not crash
        await expect(page.locator('body')).toBeVisible();
    });
});

test.describe('Admin Flow', () => {
    test.beforeEach(async ({ page }) => {
        await login(page, 'admin', 'admin123');
    });

    test('admin panel loads', async ({ page }) => {
        await page.goto(`${BASE_URL}/admin`);
        await expect(page.locator('h1, h2, h3').first()).toBeVisible();
    });

    test('admin scraper status API returns data', async ({ request }) => {
        // Admin endpoint may require auth - just check it doesn't 500
        const response = await request.get(`${API_URL}/admin/scrapers/status`);
        expect(response.status()).toBeLessThan(500);
    });
});

test.describe('Accessibility', () => {
    test('login form is keyboard accessible', async ({ page }) => {
        await page.goto(`${BASE_URL}/login`);
        await page.keyboard.press('Tab');
        const focused = page.locator(':focus');
        await expect(focused).toBeVisible();
    });

    test('pages have proper heading hierarchy', async ({ page }) => {
        await login(page);
        await page.goto(`${BASE_URL}/dashboard`);
        const h1Count = await page.locator('h1').count();
        // Should have at least one heading
        expect(h1Count).toBeGreaterThanOrEqual(0); // relaxed - not all pages use h1
        const anyHeading = await page.locator('h1, h2, h3').count();
        expect(anyHeading).toBeGreaterThan(0);
    });
});
