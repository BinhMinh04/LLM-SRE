import type { ButtonHTMLAttributes } from 'react'

const styles = {
  primary: 'bg-accent text-white hover:opacity-90 shadow-card',
  ghost: 'bg-surface border border-hair text-ink hover:bg-surface-2',
  danger: 'bg-sev-critical text-white hover:opacity-90',
}

export function Button({
  variant = 'primary',
  className = '',
  ...p
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof styles }) {
  return (
    <button
      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-50 ${styles[variant]} ${className}`}
      {...p}
    />
  )
}
