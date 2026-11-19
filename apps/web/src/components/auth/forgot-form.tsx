"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthShell, FormMessage, linkClass } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/ui/button";
import { forgotSchema, friendlyAuthError, type ForgotValues } from "@/lib/auth-schemas";
import { getSupabase } from "@/lib/supabase/client";

export function ForgotForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotValues>({ resolver: zodResolver(forgotSchema) });

  async function onSubmit({ email }: ForgotValues) {
    setFormError(null);
    const { error } = await getSupabase().auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/callback?next=/reset-password`,
    });
    if (error) {
      setFormError(friendlyAuthError(error.code, error.message));
      return;
    }
    setSent(true); // same message whether or not the address exists (no account enumeration)
  }

  return (
    <AuthShell
      title="Reset your password"
      subtitle="We'll email you a link to choose a new one."
      footer={
        <Link href="/login" className={linkClass}>
          Back to sign in
        </Link>
      }
    >
      {sent ? (
        <FormMessage tone="success">
          If an account exists for that email, a reset link is on its way.
        </FormMessage>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          {formError && <FormMessage tone="error">{formError}</FormMessage>}
          <FormField
            label="Email"
            type="email"
            autoComplete="email"
            error={errors.email}
            {...register("email")}
          />
          <Button type="submit" className="h-9 w-full" disabled={isSubmitting}>
            {isSubmitting && <Loader2 aria-hidden className="animate-spin" />}
            {isSubmitting ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
