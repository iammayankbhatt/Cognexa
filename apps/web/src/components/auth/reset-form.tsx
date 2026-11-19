"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthShell, FormMessage, linkClass } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/ui/button";
import { friendlyAuthError, MIN_PASSWORD, resetSchema, type ResetValues } from "@/lib/auth-schemas";
import { getSupabase } from "@/lib/supabase/client";

export function ResetForm() {
  const router = useRouter();
  const [hasSession, setHasSession] = useState<boolean | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetValues>({ resolver: zodResolver(resetSchema) });

  useEffect(() => {
    async function check() {
      const { data } = await getSupabase().auth.getSession();
      setHasSession(Boolean(data.session));
    }
    void check();
  }, []);

  async function onSubmit({ password }: ResetValues) {
    setFormError(null);
    const { error } = await getSupabase().auth.updateUser({ password });
    if (error) {
      setFormError(friendlyAuthError(error.code, error.message));
      return;
    }
    toast.success("Password updated.");
    router.replace("/app");
    router.refresh();
  }

  if (hasSession === false) {
    return (
      <AuthShell
        title="Link expired"
        subtitle="This reset link is invalid or has already been used."
      >
        <Link href="/forgot-password" className={`block text-center text-sm ${linkClass}`}>
          Request a new link
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Choose a new password">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {formError && <FormMessage tone="error">{formError}</FormMessage>}
        <FormField
          label="New password"
          type="password"
          autoComplete="new-password"
          hint={`At least ${MIN_PASSWORD} characters.`}
          error={errors.password}
          {...register("password")}
        />
        <FormField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm}
          {...register("confirm")}
        />
        <Button type="submit" className="h-9 w-full" disabled={isSubmitting || hasSession === null}>
          {isSubmitting && <Loader2 aria-hidden className="animate-spin" />}
          {isSubmitting ? "Saving…" : "Update password"}
        </Button>
      </form>
    </AuthShell>
  );
}
