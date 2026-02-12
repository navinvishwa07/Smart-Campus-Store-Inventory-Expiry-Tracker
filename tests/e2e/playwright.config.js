// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
    testDir: './', // Tests are in this directory
    fullyParallel: true,
    retries: 0,
    workers: '50%',
    reporter: 'html',
    use: {
        baseURL: 'http://localhost:8000',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
        // Can add firefox/webkit later if needed
    ],
    // Add webServer to start backend automatically if not running?
    // User might prefer running backend manually, but let's keep it simple for now.
});
