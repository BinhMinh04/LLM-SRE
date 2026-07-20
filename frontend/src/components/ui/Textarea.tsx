import type { TextareaHTMLAttributes } from 'react'

export function Textarea({ className = '', ...p }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-lg border border-hair bg-plane p-2 font-mono text-xs text-ink outline-none focus:border-accent ${className}`}
      {...p}
    />
  )
}
