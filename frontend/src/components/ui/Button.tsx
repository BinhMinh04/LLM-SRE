import type { ButtonHTMLAttributes } from 'react'

const styles = {
  primary: 'bg-accent text-white shadow-card hover:bg-accent-strong',
  ghost: 'border border-hair bg-surface text-ink-2 hover:bg-surface-2 hover:text-ink',
  danger: 'bg-sev-critical text-white hover:opacity-90',
}

export function Button({
  variant = 'primary',
  className = '',
  ...p
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof styles }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-semibold transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-plane disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
      {...p}
    />
  )
}
