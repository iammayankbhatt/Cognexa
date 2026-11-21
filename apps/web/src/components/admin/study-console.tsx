"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import type { Body } from "@/lib/api-contract";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, apiBlob, ApiError } from "@/lib/api";
import type { AdminStudy } from "@/lib/study";

const KEY = ["admin", "study"];

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Admin: run the user study, watch the funnel, export the anonymised CSV. */
export function StudyConsole() {
  const qc = useQueryClient();
  const { data, isPending, error, refetch } = useQuery({
    queryKey: KEY,
    queryFn: () => api<AdminStudy>("/admin/study"),
  });
  const [unlock, setUnlock] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: (body: Body<"StudyPatch">) =>
      api<AdminStudy>("/admin/study", { method: "PUT", body }),
    onSuccess: (d) => {
      qc.setQueryData(KEY, d);
      void qc.invalidateQueries({ queryKey: ["admin", "settings"] });
      toast.success("Study settings saved.");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save."),
  });
  const exportCsv = async () => {
    try {
      const blob = await apiBlob("/admin/study/export.csv");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cognexa-study-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Export failed.");
    }
  };

  if (isPending) return <Skeleton className="h-64 w-full" />;
  if (error || !data) return <ErrorState message={error?.message} onRetry={() => void refetch()} />;
  const groups = ["adaptive", "baseline"];
  const unlockValue = unlock ?? toLocalInput(data.posttest_unlock_at);
  return (
    <div className="space-y-6">
      <PageHeader
        title="User study"
        description="Adaptive vs non-adaptive recommendations (Objective 5)."
      />
      <section className="space-y-4 rounded-2xl border border-border bg-surface p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-semibold">Study is {data.enabled ? "running" : "off"}</span>
          <Button
            variant={data.enabled ? "outline" : "default"}
            disabled={save.isPending}
            onClick={() => save.mutate({ enabled: !data.enabled })}
          >
            {data.enabled ? "Stop the study" : "Start the study"}
          </Button>
          {data.started_at && (
            <span className="text-xs text-muted">
              started {new Date(data.started_at).toLocaleDateString()}
            </span>
          )}
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="space-y-1 text-sm">
            <span className="block font-medium">Group assignment</span>
            <select
              value={data.assignment}
              onChange={(e) =>
                save.mutate({ assignment: e.target.value as "random" | "alternate" })
              }
              className="h-9 w-full rounded-lg border border-border bg-bg px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="random">Random, balanced</option>
              <option value="alternate">Alternate</option>
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="block font-medium">Post-test after (days)</span>
            <input
              type="number"
              min={0}
              max={365}
              defaultValue={data.posttest_after_days}
              onBlur={(e) => save.mutate({ posttest_after_days: Number(e.target.value) })}
              className="h-9 w-full rounded-lg border border-border bg-bg px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="block font-medium">Or unlock the post-test on</span>
            <input
              type="datetime-local"
              value={unlockValue}
              onChange={(e) => setUnlock(e.target.value)}
              onBlur={() =>
                save.mutate(
                  unlockValue
                    ? { posttest_unlock_at: new Date(unlockValue).toISOString() }
                    : { clear_unlock_date: true },
                )
              }
              className="h-9 w-full rounded-lg border border-border bg-bg px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </label>
        </div>
      </section>
      <section className="space-y-3 rounded-2xl border border-border bg-surface p-5">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-semibold">Enrolment and completion</h2>
          <Button variant="outline" size="sm" className="ml-auto" onClick={() => void exportCsv()}>
            <Download aria-hidden className="size-4" /> Export anonymised CSV
          </Button>
        </div>
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted">
            <tr>
              <th className="py-1.5 font-medium">Group</th>
              <th className="py-1.5 text-right font-medium">Enrolled</th>
              <th className="py-1.5 text-right font-medium">Pre-test done</th>
              <th className="py-1.5 text-right font-medium">Post-test done</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g} className="border-t border-border">
                <td className="py-1.5 capitalize">{g}</td>
                {["enrolled", "pretest", "posttest"].map((k) => (
                  <td key={k} className="py-1.5 text-right tabular-nums">
                    {data.funnel[g]?.[k] ?? 0}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-muted">
          Withdrawn: {data.funnel.withdrawn?.count ?? 0}. The CSV holds salted participant codes,
          never names or emails.
        </p>
      </section>
    </div>
  );
}
