/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Content-surface tokens (values swap via CSS vars on [data-theme]).
        plane: 'var(--plane)',
        surface: 'var(--surface)',
        'surface-2': 'var(--surface-2)',
        ink: 'var(--ink)',
        'ink-2': 'var(--ink-2)',
        muted: 'var(--muted)',
        hair: 'var(--hair)',
        grid: 'var(--grid)',
        accent: 'var(--accent)',
        'accent-strong': 'var(--accent-strong)',
        'accent-weak': 'var(--accent-weak)',
        info: 'var(--info)',
        purple: 'var(--purple)',
        // Navigation rail — constant (dark in both themes).
        rail: 'var(--rail)',
        'rail-panel': 'var(--rail-panel)',
        'rail-text': 'var(--rail-text)',
        'rail-dim': 'var(--rail-dim)',
        'rail-hair': 'var(--rail-hair)',
        // Status palette (fixed — never themed).
        'sev-critical': 'var(--sev-critical)',
        'sev-high': 'var(--sev-high)',
        'sev-medium': 'var(--sev-medium)',
        'sev-low': 'var(--sev-low)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(2,6,23,0.04), 0 6px 16px rgba(2,6,23,0.05)',
        'card-hover': '0 2px 6px rgba(2,6,23,0.06), 0 16px 32px rgba(2,6,23,0.10)',
        rail: '0 8px 24px rgba(2,6,23,0.4)',
        // Raised-button depth: a tight contact shadow plus a soft ambient one,
        // deepening further on hover and flattening on press for tactile feedback.
        btn: '0 1px 1px rgba(2,6,23,0.07), 0 4px 8px rgba(2,6,23,0.10), 0 10px 20px rgba(2,6,23,0.08)',
        'btn-hover': '0 2px 3px rgba(2,6,23,0.09), 0 8px 16px rgba(2,6,23,0.14), 0 18px 32px rgba(2,6,23,0.12)',
        'btn-press': '0 1px 1px rgba(2,6,23,0.06)',
      },
    },
  },
  plugins: [],
}
