import {
  BarChart3,
  BookOpen,
  ClipboardCheck,
  FileText,
  Flag,
  FlaskConical,
  LayoutDashboard,
  MessageSquareText,
  Network,
  NotebookPen,
  RefreshCcw,
  Settings,
  Shield,
  SlidersHorizontal,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Lowest role that sees the item (admin pages); reviewers handle graph, content, moderation. */
  minRole?: "reviewer" | "admin";
}

export const MAIN_NAV: NavItem[] = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/tutor", label: "Tutor", icon: MessageSquareText },
  { href: "/app/learn", label: "Learn", icon: BookOpen },
  { href: "/app/graph", label: "Knowledge map", icon: Network },
  { href: "/app/quizzes", label: "Quizzes", icon: ClipboardCheck },
  { href: "/app/review", label: "Review", icon: RefreshCcw },
  { href: "/app/notes", label: "Notes", icon: NotebookPen },
  { href: "/app/settings", label: "Settings", icon: Settings },
];

export const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Overview", icon: Shield, minRole: "reviewer" },
  { href: "/admin/graph", label: "Graph editor", icon: Network, minRole: "reviewer" },
  { href: "/admin/proposals", label: "Proposals", icon: Sparkles, minRole: "reviewer" },
  { href: "/admin/content", label: "Content", icon: FileText, minRole: "reviewer" },
  { href: "/admin/moderation", label: "Moderation", icon: Flag, minRole: "reviewer" },
  { href: "/admin/evaluation", label: "Evaluation", icon: FlaskConical, minRole: "reviewer" },
  { href: "/admin/users", label: "Users", icon: Users, minRole: "admin" },
  { href: "/admin/usage", label: "AI usage", icon: BarChart3, minRole: "admin" },
  { href: "/admin/settings", label: "AI settings", icon: SlidersHorizontal, minRole: "admin" },
  { href: "/admin/study", label: "User study", icon: Users, minRole: "admin" },
];

const RANK = { student: 0, reviewer: 1, admin: 2 } as const;

/** The admin items a role may open (the server enforces the same roles on every endpoint). */
export function adminNavFor(role: keyof typeof RANK | undefined): NavItem[] {
  if (!role) return [];
  return ADMIN_NAV.filter((i) => RANK[role] >= RANK[i.minRole ?? "admin"]);
}
