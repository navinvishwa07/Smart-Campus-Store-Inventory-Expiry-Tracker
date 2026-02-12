import { defineConfig } from 'vite';

export default defineConfig({
    root: '.', // Use current directory as root
    build: {
        outDir: 'dist', // Output to dist inside frontend/ (required for Vercel)
        emptyOutDir: true,
    },
    server: {
        proxy: {
            '/api': 'http://localhost:8000', // Proxy API requests during dev
        }
    }
});
