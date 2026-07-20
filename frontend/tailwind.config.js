/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Theme tokens (values swap via CSS vars on [data-theme]).
        plane: 'var(--plane)',
        surface: 'var(--surface)',
        'surface-2': 'var(--surface-2)',
        ink: 'var(--ink)',
        'ink-2': 'var(--ink-2)',
        muted: 'var(--muted)',
        hair: 'var(--hair)',
        grid: 'var(--grid)',
        accent: 'var(--accent)',
        'accent-weak': 'var(--accent-weak)',
        // Status palette (fixed — never themed).
        'sev-critical': 'var(--sev-critical)',
        'sev-high': 'var(--sev-high)',
        'sev-medium': 'var(--sev-medium)',
        'sev-low': 'var(--sev-low)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(11,11,11,0.04), 0 1px 3px rgba(11,11,11,0.06)',
      },
    },
  },
  plugins: [],
}
