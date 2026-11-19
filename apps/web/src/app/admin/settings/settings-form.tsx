"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Loader2, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  FLAG_HELP,
  validateSection,
  type AdminSettings,
  type SectionName,
} from "@/lib/admin-settings";
import { api, ApiError } from "@/lib/api";

const KEY = ["admin", "settings"] as const;
type Values = Record<string, string>;

function useSave(section: SectionName, onErrors: (e: Record<string, string>) => void) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (raw: unknown) => {
      const v = validateSection(section, raw);
      if (!v.ok) {
        onErrors(v.errors);
        throw new Error("invalid");
      }
      onErrors({});
      return api<AdminSettings>("/admin/settings", { method: "PUT", body: { [section]: v.value } });
    },
    onSuccess: (data) => {
      qc.setQueryData(KEY, data);
      toast.success("Settings saved");
    },
    onError: (e) => {
      if (e instanceof ApiError) toast.error("Could not save", { description: e.message });
    },
  });
}

function Section({
  title,
  description,
  children,
  onSave,
  saving,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  onSave: () => void;
  saving: boolean;
}) {
  return (
    <form
      className="space-y-4 rounded-2xl border border-border bg-surface p-5"
      onSubmit={(e) => {
        e.preventDefault();
        onSave();
      }}
      noValidate
    >
      <div>
        <h2 className="text-lg font-semibold text-text">{title}</h2>
        <p className="text-sm text-muted">{description}</p>
      </div>
      {children}
      <Button type="submit" size="sm" disabled={saving}>
        {saving && <Loader2 className="animate-spin" aria-hidden />}
        Save
      </Button>
    </form>
  );
}

function NumberField({
  id,
  label,
  value,
  error,
  onChange,
  step = "1",
}: {
  id: string;
  label: string;
  value: string;
  error?: string;
  onChange: (v: string) => void;
  step?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        inputMode="decimal"
        type="number"
        step={step}
        value={value}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
      {error && (
        <p id={`${id}-error`} className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

const asStrings = (o: Record<string, number>): Values =>
  Object.fromEntries(Object.entries(o).map(([k, v]) => [k, String(v)]));

function NumbersSection({
  section,
  title,
  description,
  initial,
  labels,
  step,
}: {
  section: SectionName;
  title: string;
  description: string;
  initial: Record<string, number>;
  labels: Record<string, string>;
  step?: string;
}) {
  const [values, setValues] = useState<Values>(asStrings(initial));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const save = useSave(section, setErrors);
  return (
    <Section
      title={title}
      description={description}
      onSave={() => save.mutate(values)}
      saving={save.isPending}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {Object.entries(labels).map(([field, label]) => (
          <NumberField
            key={field}
            id={`${section}-${field}`}
            label={label}
            step={step}
            value={values[field] ?? ""}
            error={errors[field]}
            onChange={(v) => setValues((s) => ({ ...s, [field]: v }))}
          />
        ))}
      </div>
    </Section>
  );
}

function Toggle({
  id,
  label,
  help,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  help?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-surface-2 p-3"
    >
      <input
        id={id}
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 size-4 accent-[var(--primary)]"
      />
      <span>
        <span className="block text-sm font-medium text-text">{label}</span>
        {help && <span className="block text-xs text-muted">{help}</span>}
      </span>
    </label>
  );
}

function CacheSection({ initial }: { initial: AdminSettings["cache"] }) {
  const [enabled, setEnabled] = useState(initial.enabled);
  const [values, setValues] = useState<Values>(
    asStrings({
      response_ttl_days: initial.response_ttl_days,
      classification_ttl_days: initial.classification_ttl_days,
      embedding_ttl_days: initial.embedding_ttl_days,
    }),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const save = useSave("cache", setErrors);
  const labels: Record<string, string> = {
    response_ttl_days: "Answers (days)",
    classification_ttl_days: "Classifications (days)",
    embedding_ttl_days: "Query embeddings (days)",
  };
  return (
    <Section
      title="Cache"
      description="Cached answers still count as one request but use no tokens. Entries are invalidated when a concept's content or edges change, or the answer is reported."
      onSave={() => save.mutate({ enabled, ...values })}
      saving={save.isPending}
    >
      <Toggle id="cache-enabled" label="Caching enabled" checked={enabled} onChange={setEnabled} />
      <div className="grid gap-3 sm:grid-cols-3">
        {Object.entries(labels).map(([f, l]) => (
          <NumberField
            key={f}
            id={`cache-${f}`}
            label={l}
            step="0.5"
            value={values[f] ?? ""}
            error={errors[f]}
            onChange={(v) => setValues((s) => ({ ...s, [f]: v }))}
          />
        ))}
      </div>
    </Section>
  );
}

function FeaturesSection({ initial }: { initial: AdminSettings["features"] }) {
  const [flags, setFlags] = useState(initial);
  const save = useSave("features", () => undefined);
  return (
    <Section
      title="Feature flags"
      description="Take effect immediately for everyone."
      onSave={() => save.mutate(flags)}
      saving={save.isPending}
    >
      <div className="space-y-2">
        {(Object.keys(FLAG_HELP) as (keyof typeof FLAG_HELP)[]).map((name) => (
          <Toggle
            key={name}
            id={`flag-${name}`}
            label={name}
            help={FLAG_HELP[name]}
            checked={flags[name]}
            onChange={(v) => setFlags((f) => ({ ...f, [name]: v }))}
          />
        ))}
      </div>
    </Section>
  );
}

interface PriceRow {
  model: string;
  input: string;
  output: string;
}

function PricingSection({ initial }: { initial: AdminSettings["pricing"] }) {
  const [def, setDef] = useState<Values>(asStrings(initial.default));
  const [rows, setRows] = useState<PriceRow[]>(
    Object.entries(initial.models).map(([model, p]) => ({
      model,
      input: String(p.input_per_1m),
      output: String(p.output_per_1m),
    })),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const save = useSave("pricing", setErrors);
  const submit = () => {
    const models = Object.fromEntries(
      rows
        .filter((r) => r.model.trim())
        .map((r) => [r.model.trim(), { input_per_1m: r.input, output_per_1m: r.output }]),
    );
    save.mutate({ default: def, models });
  };
  return (
    <Section
      title="Notional pricing"
      description="US dollars per 1M tokens, used to estimate what usage would cost at scale. Model ids must match the ones configured in the backend environment."
      onSave={submit}
      saving={save.isPending}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <NumberField
          id="price-in"
          label="Default input $/1M"
          step="0.01"
          value={def.input_per_1m ?? ""}
          error={errors["default.input_per_1m"]}
          onChange={(v) => setDef((d) => ({ ...d, input_per_1m: v }))}
        />
        <NumberField
          id="price-out"
          label="Default output $/1M"
          step="0.01"
          value={def.output_per_1m ?? ""}
          error={errors["default.output_per_1m"]}
          onChange={(v) => setDef((d) => ({ ...d, output_per_1m: v }))}
        />
      </div>
      <div className="space-y-2">
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[1fr_6rem_6rem_auto] items-end gap-2">
            <div className="space-y-1.5">
              <Label htmlFor={`pm-${i}`}>Model id</Label>
              <Input
                id={`pm-${i}`}
                value={r.model}
                maxLength={120}
                onChange={(e) =>
                  setRows((rs) => rs.map((x, j) => (j === i ? { ...x, model: e.target.value } : x)))
                }
              />
            </div>
            <NumberField
              id={`pi-${i}`}
              label="In"
              step="0.01"
              value={r.input}
              onChange={(v) =>
                setRows((rs) => rs.map((x, j) => (j === i ? { ...x, input: v } : x)))
              }
            />
            <NumberField
              id={`po-${i}`}
              label="Out"
              step="0.01"
              value={r.output}
              onChange={(v) =>
                setRows((rs) => rs.map((x, j) => (j === i ? { ...x, output: v } : x)))
              }
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={`Remove ${r.model || "row"}`}
              onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}
            >
              <Trash2 aria-hidden />
            </Button>
          </div>
        ))}
        {Object.keys(errors).some((k) => k.startsWith("models")) && (
          <p className="text-xs text-danger">Check the per-model prices (0 to 1000).</p>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setRows((rs) => [...rs, { model: "", input: "0", output: "0" }])}
        >
          <Plus aria-hidden /> Add model price
        </Button>
      </div>
    </Section>
  );
}

function ProvidersPanel({ p }: { p: AdminSettings["providers"] }) {
  const rows: [string, string][] = [
    ["Primary", `${p.primary.provider} / ${p.primary.model}`],
    ["Fallback", p.fallback.provider ? `${p.fallback.provider} / ${p.fallback.model}` : "none"],
    ["Judge", `${p.judge.provider} / ${p.judge.model}`],
    ["Embeddings", `${p.embedding.provider} / ${p.embedding.model} (${p.embedding.dim} dims)`],
  ];
  return (
    <section className="space-y-3 rounded-2xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Providers</h2>
      <p className="text-sm text-muted">
        Set in the backend environment (LLM_* and EMBEDDING_* variables), not here. Keys are never
        shown, only whether they are set.
      </p>
      <dl className="space-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted">{k}</dt>
            <dd className="font-mono text-text">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="flex flex-wrap gap-2">
        {(["groq", "gemini"] as const).map((k) => (
          <Badge key={k} variant={p.keys[k] ? "default" : "outline"}>
            <KeyRound aria-hidden /> {k}: {p.keys[k] ? "set" : "missing"}
          </Badge>
        ))}
      </div>
    </section>
  );
}

export function SettingsForm() {
  const q = useQuery({ queryKey: KEY, queryFn: () => api<AdminSettings>("/admin/settings") });
  return (
    <div className="space-y-6">
      <PageHeader
        title="AI settings"
        description="Quotas, limits, caching, feature flags and notional pricing. Every change is written to the audit log."
      />
      {q.isPending ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      ) : q.isError ? (
        <ErrorState
          message="We couldn't load the settings."
          requestId={q.error instanceof ApiError ? q.error.requestId : undefined}
          onRetry={() => void q.refetch()}
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <NumbersSection
            section="quota"
            title="Student quotas"
            description="Defaults for students; reviewers and admins get these multiplied. Per-user overrides live under Users."
            initial={q.data.quota}
            labels={{
              daily_ai_requests: "AI requests per day",
              per_minute: "Requests per minute",
              max_input_chars: "Max question length (chars)",
              max_output_tokens: "Max answer length (tokens)",
            }}
          />
          <NumbersSection
            section="role_multipliers"
            title="Role multipliers"
            description="Daily and per-minute limits are multiplied by these for each role."
            initial={q.data.role_multipliers}
            labels={{ student: "Student", reviewer: "Reviewer", admin: "Admin" }}
          />
          <NumbersSection
            section="global_cap"
            title="Global daily cap"
            description="AI requests per day for everyone together; protects the free-tier provider quotas."
            initial={q.data.global_cap}
            labels={{ ai_requests: "AI requests per day (all users)" }}
          />
          <FeaturesSection initial={q.data.features} />
          <CacheSection initial={q.data.cache} />
          <PricingSection initial={q.data.pricing} />
          <ProvidersPanel p={q.data.providers} />
        </div>
      )}
    </div>
  );
}
