import { AlertTriangle, BellRing, BookOpen, LayoutDashboard, Settings, type LucideIcon } from 'lucide-react'

export type View = 'overview' | 'incidents' | 'knowledge'

export interface NavItem {
  view: View
  label: string
  icon: LucideIcon
}

/** Active destinations wired to real endpoints. */
export const NAV: NavItem[] = [
  { view: 'overview', label: 'Overview', icon: LayoutDashboard },
  { view: 'incidents', label: 'Incidents', icon: AlertTriangle },
  { view: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
]

/** Placeholders for the full project vision — shown disabled until built. */
export const NAV_SOON: { label: string; icon: LucideIcon }[] = [
  { label: 'Alerts', icon: BellRing },
  { label: 'Settings', icon: Settings },
]

export const VIEW_META: Record<View, { title: string; subtitle: string }> = {
  overview: { title: 'Overview', subtitle: 'Incident posture and knowledge base at a glance' },
  incidents: { title: 'Incidents', subtitle: 'Ingest, triage, and inspect AI analysis with evidence' },
  knowledge: { title: 'Knowledge Base', subtitle: 'Documents indexed for retrieval-augmented analysis' },
}
