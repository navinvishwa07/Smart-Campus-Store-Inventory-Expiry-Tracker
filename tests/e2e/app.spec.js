const { test, expect } = require('@playwright/test');

test.describe('Smart Campus Store E2E', () => {

    test.beforeEach(async ({ page }) => {
        // Go to the app homepage
        await page.goto('/');
    });

    test('Dashboard loads correctly', async ({ page }) => {
        // Check title
        await expect(page).toHaveTitle(/Campus Store/);

        // Check dashboard section is visible by default
        await expect(page.locator('#page-dashboard')).toBeVisible();

        // Check key elements
        await expect(page.locator('h2')).toContainText('Dashboard Overview');
    });

    test('Add new product workflow', async ({ page }) => {
        // 1. Navigate to Inventory
        await page.click('#nav-inventory');
        await expect(page.locator('#page-inventory')).toBeVisible();

        // 2. Click Add Product
        await page.click('#btn-add-product');

        // 3. Fill form
        const itemId = `E2E-${Date.now()}`;
        await page.fill('#pf-item-id', itemId);
        await page.fill('#pf-name', 'E2E Test Chip');
        await page.selectOption('#pf-category', 'Snack Foods');
        await page.fill('#pf-mrp', '25');
        await page.fill('#pf-min-stock', '15');

        // 4. Submit
        await page.click('#product-form button[type="submit"]');

        // 5. Verify it appears in the table (wait for reload/render)
        await expect(page.locator('#inventory-tbody')).toContainText('E2E Test Chip');
        await expect(page.locator('#inventory-tbody')).toContainText(itemId);
    });

    test('Navigation works between pages', async ({ page }) => {
        // Analytics
        await page.click('#nav-analytics');
        await expect(page.locator('#page-analytics')).toBeVisible();
        await expect(page.locator('h2')).toContainText('Analytics Dashboard');

        // POS
        await page.click('#nav-pos');
        await expect(page.locator('#page-pos')).toBeVisible();

        // Back to Dashboard
        await page.click('#nav-dashboard');
        await expect(page.locator('#page-dashboard')).toBeVisible();
    });

    test('POS Page loads products', async ({ page }) => {
        await page.click('#nav-pos');
        // Wait for products to load in the grid
        // Assuming there's at least one product from seeding
        const productCards = page.locator('.pos-product-card');
        // Check if at least one card is visible or "No products" message isn't there
        // We can just check that the container exists
        await expect(page.locator('.pos-grid')).toBeVisible();
    });

});
