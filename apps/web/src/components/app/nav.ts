import {
  BarChart3,
  BookOpen,
  ClipboardCheck,
  FlaskConical,
  LayoutDashboard,
  MessageSquareText,
  Network,
  NotebookPen,
  RefreshCcw,
  Settings,
  Shield,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
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
  { href: "/admin", label: "Overview", icon: Shield },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/usage", label: "AI usage", icon: BarChart3 },
  { href: "/admin/settings", label: "AI settings", icon: SlidersHorizontal },
  { href: "/admin/evaluation", label: "Evaluation", icon: FlaskConical },
  { href: "/admin/study", label: "User study", icon: Users },
];
