import {
  BookOpen,
  ClipboardCheck,
  LayoutDashboard,
  MessageSquareText,
  NotebookPen,
  RefreshCcw,
  Settings,
  Shield,
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
  { href: "/app/quizzes", label: "Quizzes", icon: ClipboardCheck },
  { href: "/app/review", label: "Review", icon: RefreshCcw },
  { href: "/app/notes", label: "Notes", icon: NotebookPen },
  { href: "/app/settings", label: "Settings", icon: Settings },
];

export const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Overview", icon: Shield },
  { href: "/admin/users", label: "Users", icon: Users },
];
