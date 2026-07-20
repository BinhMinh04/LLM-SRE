import {
  AlertTriangle,
  BookOpen,
  LayoutDashboard,
  Server,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react'

export type View = 'overview' | 'incidents' | 'knowledge'

export interface NavItem {
  view: View
  label: string
  icon: LucideIcon
}

export interface SoonItem {
  label: string
  icon: LucideIcon
}

export interface NavSection {
  heading: string
  items: NavItem[]
  soon?: SoonItem[]
}

/**
 * Sidebar structure. `items` are wired to real endpoints; `soon` entries are
 * honest placeholders for the wider project vision, shown disabled.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    heading: 'Overview',
    items: [{ view: 'overview', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    heading: 'Operations',
    items: [
      { view: 'incidents', label: 'Incidents', icon: AlertTriangle },
      { view: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
    ],
  },
  {
    heading: 'System',
    items: [],
    soon: [
      { label: 'Services', icon: Server },
      { label: 'Team', icon: Users },
      { label: 'Settings', icon: Settings },
    ],
  },
]

export const VIEW_META: Record<View, { title: string; subtitle: string }> = {
  overview: {
    title: 'Dashboard',
    subtitle: 'Incident posture, knowledge base, and live backend health',
  },
  incidents: {
    title: 'Incidents',
    subtitle: 'Ingest, triage, and inspect AI analysis with cited evidence',
  },
  knowledge: {
    title: 'Knowledge Base',
    subtitle: 'Documents indexed for retrieval-augmented analysis',
  },
}
