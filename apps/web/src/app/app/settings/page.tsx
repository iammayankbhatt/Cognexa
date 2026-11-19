"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Download, Loader2, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ME_KEY, useMe } from "@/components/app/me-provider";
import { FormMessage } from "@/components/auth/auth-shell";
import { PageHeader } from "@/components/shared/page-header";
import { useTheme } from "@/components/theme/theme-provider";
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
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError, type Me } from "@/lib/api";
import { getSupabase } from "@/lib/supabase/client";
import { THEMES } from "@/lib/themes";
import { cn } from "@/lib/utils";

function ThemePreview({
  id,
  label,
  description,
}: {
  id: string;
  label: string;
  description: string;
}) {
  const { theme, setTheme } = useTheme();
  const active = theme === id;
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={() => setTheme(id as typeof theme)}
      className={cn(
        "flex flex-col gap-3 rounded-xl border p-3 text-left transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active ? "border-accent" : "border-border hover:border-muted",
      )}
    >
      {/* Scoped to its own theme so each card shows the real colours of that theme. */}
      <span
        data-theme={id}
        aria-hidden
        className="block space-y-2 rounded-lg border border-border bg-bg p-3"
      >
        <span className="block h-2 w-1/2 rounded-full bg-text" />
        <span className="block h-2 w-3/4 rounded-full bg-muted" />
        <span className="flex gap-2 pt-1">
          <span className="h-5 w-14 rounded-md bg-primary" />
          <span className="h-5 w-10 rounded-md bg-accent" />
          <span className="h-5 w-8 rounded-md bg-surface-2" />
        </span>
      </span>
      <span className="flex items-center justify-between">
        <span>
          <span className="block text-sm font-medium text-text">{label}</span>
          <span className="block text-xs text-muted">{description}</span>
        </span>
        {active && <Check aria-hidden className="size-4 text-accent" />}
      </span>
    </button>
  );
}

function ProfileCard({ me }: { me: Me }) {
  const qc = useQueryClient();
  const [name, setName] = useState(me.display_name ?? "");
  const save = useMutation({
    mutationFn: () => api<Me>("/me", { method: "PATCH", body: { display_name: name.trim() } }),
    onSuccess: (next) => {
      qc.setQueryData(ME_KEY, next);
      toast.success("Profile saved.");
    },
  });
  const invalid = name.trim().length === 0 || name.trim().length > 80;
  return (
    <section className="space-y-4 rounded-2xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Profile</h2>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!invalid) save.mutate();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="display-name">Display name</Label>
          <Input
            id="display-name"
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
            aria-invalid={invalid || undefined}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" value={me.email ?? ""} readOnly disabled />
        </div>
        {save.error && (
          <FormMessage tone="error">
            {save.error instanceof ApiError ? save.error.message : "Could not save."}
          </FormMessage>
        )}
        <Button
          type="submit"
          className="h-9"
          disabled={invalid || save.isPending || name.trim() === me.display_name}
        >
          {save.isPending && <Loader2 aria-hidden className="animate-spin" />}
          Save
        </Button>
      </form>
    </section>
  );
}

function DataCard() {
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const qc = useQueryClient();

  async function exportData() {
    setBusy(true);
    try {
      const data = await api<unknown>("/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "cognexa-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  }

  const del = useMutation({
    mutationFn: () => api("/me", { method: "DELETE", body: { confirm: "DELETE" } }),
    onSuccess: async () => {
      await getSupabase().auth.signOut();
      qc.clear();
      toast.success("Your account has been deleted.");
      router.replace("/");
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not delete the account."),
  });

  function setDialog(next: boolean) {
    setOpen(next);
    if (!next) {
      setConfirm("");
      setError(null);
    }
  }

  return (
    <section className="space-y-4 rounded-2xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Your data</h2>
      <p className="text-sm text-muted">
        Download everything Cognexa stores about you as a JSON file, or delete your account and all
        of its data permanently.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" className="h-9" onClick={() => void exportData()} disabled={busy}>
          {busy ? <Loader2 aria-hidden className="animate-spin" /> : <Download aria-hidden />}
          Export my data
        </Button>
        <Button variant="destructive" className="h-9" onClick={() => setDialog(true)}>
          <Trash2 aria-hidden /> Delete account
        </Button>
      </div>
      <Dialog open={open} onOpenChange={setDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete your account?</DialogTitle>
            <DialogDescription>
              This removes your profile, quiz history, mastery, chats and notes. It cannot be
              undone. Type <strong>DELETE</strong> to confirm.
            </DialogDescription>
          </DialogHeader>
          <Input
            aria-label="Type DELETE to confirm"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="off"
          />
          {error && <FormMessage tone="error">{error}</FormMessage>}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={confirm !== "DELETE" || del.isPending}
              onClick={() => del.mutate()}
            >
              {del.isPending && <Loader2 aria-hidden className="animate-spin" />}
              Delete permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

export default function SettingsPage() {
  const { data: me, isPending } = useMe();
  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Your profile, appearance and data." />
      {isPending || !me ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <ProfileCard me={me} />
          <section className="space-y-4 rounded-2xl border border-border bg-surface p-5">
            <h2 className="text-lg font-semibold text-text">Appearance</h2>
            <p className="text-sm text-muted">
              Saved to your profile, so it follows you across devices. Use Titanium Light on
              projectors.
            </p>
            <div role="radiogroup" aria-label="Colour theme" className="grid gap-3 sm:grid-cols-3">
              {THEMES.map((t) => (
                <ThemePreview key={t.id} id={t.id} label={t.label} description={t.description} />
              ))}
            </div>
          </section>
          <DataCard />
        </div>
      )}
    </div>
  );
}
