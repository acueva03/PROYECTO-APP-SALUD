import globals from 'globals';

export default [
  {
    files: ['frontend/static/**/*.js'],
    ignores: ['frontend/static/chart.umd.min.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'script',
       globals: { ...globals.browser, Chart: 'readonly', Html5Qrcode: 'readonly' }
    },
    rules: {
      'no-undef': 'error',
      'no-empty': 'warn',
      'no-unused-vars': ['warn', { caughtErrors: 'none' }]
    }
  }
];