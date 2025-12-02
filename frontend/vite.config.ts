/// <reference types="vitest" />
import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            }
        }
    },
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: './setupTests.ts',
        include: ['**/*.test.{ts,tsx}', 'src/**/*.{test,spec}.{ts,tsx}'],  // Add test directory
        coverage: {
            provider: 'v8',
            reporter: ['text', 'html', 'json'],
            all: true,
            include: ['src/**/*.{ts,tsx}'],
            exclude: ['**/*.test.{ts,tsx}', '**/tests/**'],
        },
        typecheck: {
            tsconfig: './tsconfig.json',
        },
    }
})
