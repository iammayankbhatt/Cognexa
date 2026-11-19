"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, MailCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthShell, FormMessage, linkClass } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Divider, GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import {
  friendlyAuthError,
  MIN_PASSWORD,
  signupSchema,
  type SignupValues,
} from "@/lib/auth-schemas";
import { getSupabase } from "@/lib/supabase/client";

export function SignupForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({ resolver: zodResolver(signupSchema) });

  async function onSubmit(v: SignupValues) {
    setFormError(null);
    const { data, error } = await getSupabase().auth.signUp({
      email: v.email,
      password: v.password,
      options: {
        data: { full_name: v.name },
        emailRedirectTo: `${window.location.origin}/auth/callback?next=/app`,
      },
    });
    if (error) {
      setFormError(friendlyAuthError(error.code, error.message));
      return;
    }
    // With confirmations on, an existing address returns a user with no identities (no email sent).
    if (data.user && data.user.identities?.length === 0) {
      setFormError(friendlyAuthError("user_already_exists", ""));
      return;
    }
    setSentTo(v.email);
  }

  if (sentTo) {
    return (
      <AuthShell title="Check your inbox" subtitle="One more step to activate your account.">
        <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-surface-2 px-4 py-6 text-center">
          <MailCheck aria-hidden className="size-8 text-accent" />
          <p className="text-sm text-text">
            We sent a confirmation link to <strong className="break-all">{sentTo}</strong>. Open it
            to finish signing up.
          </p>
          <p className="text-xs text-muted">
            Nothing arrived? Check spam, or try again in a minute.
          </p>
        </div>
        <Link href="/login" className={`block text-center text-sm ${linkClass}`}>
          Back to sign in
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Learn DSA with a tutor that knows what you're missing."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className={linkClass}>
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {formError && <FormMessage tone="error">{formError}</FormMessage>}
        <FormField label="Name" autoComplete="name" error={errors.name} {...register("name")} />
        <FormField
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email}
          {...register("email")}
        />
        <FormField
          label="Password"
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
        <Button type="submit" className="h-9 w-full" disabled={isSubmitting}>
          {isSubmitting && <Loader2 aria-hidden className="animate-spin" />}
          {isSubmitting ? "Creating account…" : "Create account"}
        </Button>
        <p className="text-xs text-muted">
          By signing up you agree to the{" "}
          <Link href="/terms" className={linkClass}>
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className={linkClass}>
            Privacy Policy
          </Link>
          .
        </p>
      </form>
      <Divider />
      <GoogleButton next="/app" onError={setFormError} />
    </AuthShell>
  );
}
