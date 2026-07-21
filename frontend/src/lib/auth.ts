import { useState } from 'react'

/**
 * Frontend-only auth gate. There is no real backend auth yet (M6 is unbuilt), so this just
 * records "someone signed in" — the email they typed — in Web Storage and gates the dashboard on
 * its presence. "Remember me" picks the store: localStorage (survives restarts) vs sessionStorage
 * (cleared when the tab closes). Swap this for real OAuth/JWT when M6 lands.
 */
const AUTH_KEY = 'iim-auth'

function readEmail(): string | null {
  return localStorage.getItem(AUTH_KEY) ?? sessionStorage.getItem(AUTH_KEY)
}

export function useAuth() {
  const [email, setEmail] = useState<string | null>(readEmail)

  const signIn = (userEmail: string, remember = true) => {
    const value = userEmail.trim() || 'guest@iim.local'
    // Keep one source of truth: clear the other store so remember-me semantics stay clean.
    ;(remember ? sessionStorage : localStorage).removeItem(AUTH_KEY)
    ;(remember ? localStorage : sessionStorage).setItem(AUTH_KEY, value)
    setEmail(value)
  }

  const signOut = () => {
    localStorage.removeItem(AUTH_KEY)
    sessionStorage.removeItem(AUTH_KEY)
    setEmail(null)
  }

  return { authed: email !== null, email, signIn, signOut }
}
