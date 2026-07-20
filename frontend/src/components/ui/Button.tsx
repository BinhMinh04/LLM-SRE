import type { ButtonHTMLAttributes } from 'react'

const styles = {
  primary: 'bg-accent text-white shadow-btn hover:bg-accent-strong hover:shadow-btn-hover',
  ghost: 'border border-hair bg-surface text-ink-2 shadow-btn hover:bg-surface-2 hover:text-ink hover:shadow-btn-hover',
  danger: 'bg-sev-critical text-white shadow-btn hover:opacity-90 hover:shadow-btn-hover',
}

export function Button({
  variant = 'primary',
  className = '',
  ...p
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof styles }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-2xl px-3.5 py-2 text-sm font-semibold tracking-tight transition duration-150 active:translate-y-px active:shadow-btn-press focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-plane disabled:cursor-not-allowed disabled:opacity-50 disabled:active:translate-y-0 disabled:active:shadow-btn ${styles[variant]} ${className}`}
      {...p}
    />
  )
}
