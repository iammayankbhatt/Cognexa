"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Ban, ChevronLeft, ChevronRight, Search, UserCheck, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import type { Body } from "@/lib/api-contract";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserUsage } from "@/lib/admin";
import { api, ApiError } from "@/lib/api";

interface AdminUser {
  id: string;
  email: string | null;
  display_name: string | null;
  role: "student" | "reviewer" | "admin";
  study_group: "adaptive" | "baseline" | "none";
  quota_override: { daily_ai_requests: number } | null;
  disabled_at: string | null;
  created_at: string | null;
}
interface Page {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}
interface Patch {
  role?: AdminUser["role"];
  study_group?: AdminUser["study_group"];
  quota_override?: { daily_ai_requests: number };
  clear_quota_override?: boolean;
  disabled?: boolean;
}

const selectClass =
  "h-8 rounded-lg border border-border bg-surface px-2 text-sm text-text outline-none focus-visible:ring-2 focus-visible:ring-ring";

function UsageDialog({ user, onClose }: { user: AdminUser | null; onClose: () => void }) {
  const { data, isPending, error, refetch } = useUserUsage(user?.id ?? null);
  const label = user ? (user.display_name ?? user.email ?? user.id) : "";
  return (
    <Dialog open={user !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Usage: {label}</DialogTitle>
          <DialogDescription>
            Last 30 days of AI requests and activity counts. Chat contents are not shown (privacy
            policy); reported answers are visible under Moderation.
          </DialogDescription>
        </DialogHeader>
        {isPending ? (
          <Skeleton className="h-40 w-full" aria-label="Loading usage" />
        ) : error ? (
          <ErrorState message={error.message} onRetry={() => void refetch()} />
        ) : (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              {(
                [
                  ["AI requests", data.totals.ai_requests],
                  ["Est. cost", `$${data.totals.est_cost_usd.toFixed(4)}`],
                  ["Tutor questions", data.totals.tutor_questions],
                  ["Quizzes", data.totals.quizzes],
                  ["Reports filed", data.totals.reports_filed],
                ] as const
              ).map(([k, v]) => (
                <div key={k} className="rounded-lg border border-border bg-surface-2/40 p-3">
                  <dt className="text-xs text-muted">{k}</dt>
                  <dd className="text-lg font-semibold">{v}</dd>
                </div>
              ))}
            </dl>
            {data.history.length === 0 ? (
              <p className="text-sm text-muted">No AI requests in this period.</p>
            ) : (
              <div className="max-h-60 overflow-y-auto rounded-lg border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-muted uppercase">
                    <tr>
                      <th className="px-3 py-2 font-medium">Date</th>
                      <th className="px-3 py-2 font-medium">Requests</th>
                      <th className="px-3 py-2 font-medium">Tokens in / out</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.history].reverse().map((h) => (
                      <tr key={h.date} className="border-t border-border">
                        <td className="px-3 py-1.5">{h.date}</td>
                        <td className="px-3 py-1.5">{h.ai_requests}</td>
                        <td className="px-3 py-1.5">
                          {h.tokens_in} / {h.tokens_out}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function UserRow({
  user,
  onUsage,
  onDisable,
}: {
  user: AdminUser;
  onUsage: (u: AdminUser) => void;
  onDisable: (u: AdminUser) => void;
}) {
  const qc = useQueryClient();
  const [quota, setQuota] = useState(user.quota_override?.daily_ai_requests?.toString() ?? "");
  const patch = useMutation({
    mutationFn: (body: Patch & Body<"UserPatch">) =>
      api<AdminUser>(`/admin/users/${user.id}`, { method: "PATCH", body }),
    onSuccess: () => {
      toast.success("User updated.");
      void qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Update failed."),
  });
  const label = user.display_name ?? user.email ?? user.id;

  return (
    <tr className="border-t border-border">
      <td className="px-3 py-3">
        <div className="font-medium text-text">{label}</div>
        <div className="text-xs text-muted">{user.email}</div>
        {user.disabled_at && (
          <Badge variant="outline" className="mt-1 border-danger text-danger">
            disabled
          </Badge>
        )}
      </td>
      <td className="px-3 py-3">
        <select
          aria-label={`Role for ${label}`}
          className={selectClass}
          value={user.role}
          disabled={patch.isPending}
          onChange={(e) => patch.mutate({ role: e.target.value as AdminUser["role"] })}
        >
          <option value="student">student</option>
          <option value="reviewer">reviewer</option>
          <option value="admin">admin</option>
        </select>
      </td>
      <td className="px-3 py-3">
        <select
          aria-label={`Study group for ${label}`}
          className={selectClass}
          value={user.study_group}
          disabled={patch.isPending}
          onChange={(e) =>
            patch.mutate({ study_group: e.target.value as AdminUser["study_group"] })
          }
        >
          <option value="none">none</option>
          <option value="adaptive">adaptive</option>
          <option value="baseline">baseline</option>
        </select>
      </td>
      <td className="px-3 py-3">
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const n = Number(quota);
            if (quota.trim() === "") patch.mutate({ clear_quota_override: true });
            else if (Number.isInteger(n) && n >= 0 && n <= 10000)
              patch.mutate({ quota_override: { daily_ai_requests: n } });
            else
              toast.error("Enter a whole number from 0 to 10000, or leave blank for the default.");
          }}
        >
          <Input
            aria-label={`Daily AI request quota for ${label}`}
            className="w-24"
            inputMode="numeric"
            placeholder="default"
            value={quota}
            onChange={(e) => setQuota(e.target.value)}
          />
          <Button type="submit" size="sm" variant="outline" disabled={patch.isPending}>
            Set
          </Button>
        </form>
      </td>
      <td className="px-3 py-3">
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => onUsage(user)}>
            <Activity aria-hidden className="size-4" /> Usage
          </Button>
          {user.disabled_at ? (
            <Button
              size="sm"
              variant="outline"
              disabled={patch.isPending}
              onClick={() => patch.mutate({ disabled: false })}
            >
              <UserCheck aria-hidden className="size-4" /> Enable
            </Button>
          ) : (
            <Button size="sm" variant="outline" onClick={() => onDisable(user)}>
              <Ban aria-hidden className="size-4" /> Disable
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

export function AdminUsersTable() {
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(1);
  const [usageFor, setUsageFor] = useState<AdminUser | null>(null);
  const [disabling, setDisabling] = useState<AdminUser | null>(null);
  const qc = useQueryClient();
  const disable = useMutation({
    mutationFn: (u: AdminUser) =>
      api<AdminUser>(`/admin/users/${u.id}`, {
        method: "PATCH",
        body: { disabled: true } satisfies Body<"UserPatch">,
      }),
    onSuccess: () => {
      toast.success("Account disabled. Every API call from it is now refused.");
      setDisabling(null);
      void qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not disable it."),
  });
  const query = useQuery({
    queryKey: ["admin-users", term, page],
    queryFn: () =>
      api<Page>(
        `/admin/users?page=${page}&page_size=25${term ? `&q=${encodeURIComponent(term)}` : ""}`,
      ),
    placeholderData: (prev) => prev,
  });
  const pages = query.data ? Math.max(1, Math.ceil(query.data.total / query.data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="Change roles, study groups and daily AI quotas, view usage, or disable an account. Every change is recorded in the audit log."
      />
      <form
        className="flex max-w-md gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          setTerm(q.trim());
        }}
      >
        <Input
          aria-label="Search users"
          placeholder="Search by name or email"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Button type="submit" variant="outline">
          <Search aria-hidden /> Search
        </Button>
      </form>

      {query.isPending ? (
        <Skeleton className="h-64 w-full" aria-label="Loading users" />
      ) : query.error ? (
        <ErrorState
          message={query.error.message}
          requestId={query.error instanceof ApiError ? query.error.requestId : undefined}
          onRetry={() => void query.refetch()}
        />
      ) : query.data.items.length === 0 ? (
        <EmptyState icon={<Users />} title="No users found" description="Try a different search." />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-border bg-surface">
            <table className="w-full min-w-[52rem] text-left text-sm">
              <thead className="text-xs text-muted uppercase">
                <tr>
                  <th className="px-3 py-2 font-medium">User</th>
                  <th className="px-3 py-2 font-medium">Role</th>
                  <th className="px-3 py-2 font-medium">Study group</th>
                  <th className="px-3 py-2 font-medium">Daily AI quota</th>
                  <th className="px-3 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((u) => (
                  <UserRow
                    key={`${u.id}-${u.role}-${u.study_group}-${u.disabled_at ?? ""}`}
                    user={u}
                    onUsage={setUsageFor}
                    onDisable={setDisabling}
                  />
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between text-sm text-muted">
            <span>
              {query.data.total} user{query.data.total === 1 ? "" : "s"} · page {page} of {pages}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft aria-hidden />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pages}
                onClick={() => setPage((p) => p + 1)}
                aria-label="Next page"
              >
                <ChevronRight aria-hidden />
              </Button>
            </div>
          </div>
        </>
      )}
      <UsageDialog user={usageFor} onClose={() => setUsageFor(null)} />
      <Dialog open={disabling !== null} onOpenChange={(o) => !o && setDisabling(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Disable this account?</DialogTitle>
            <DialogDescription>
              {disabling?.email ?? disabling?.id} will be refused on every API call until you enable
              the account again. Their data is kept.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisabling(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={disable.isPending}
              onClick={() => disabling && disable.mutate(disabling)}
            >
              Disable account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
