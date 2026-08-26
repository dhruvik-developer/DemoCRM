import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // dist = build output; src/components/ui = generated shadcn/ui files (do not
  // hand-edit); public/mockServiceWorker.js = generated MSW worker script.
  globalIgnores([
    'dist',
    'src/components/ui/**',
    'public/mockServiceWorker.js',
  ]),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
  {
    // Node-context configs (Playwright, Vite, ESLint itself).
    files: ['*.config.js', 'playwright.config.js'],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
])
