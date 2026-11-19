"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthShell, FormMessage, linkClass } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Divider, GoogleButton } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { friendlyAuthError, loginSchema, safeNext, type LoginValues } from "@/lib/auth-schemas";
import { getSupabase } from "@/lib/supabase/client";

const URL_ERRORS: Record<string, string> = {
  auth_not_configured:
    "Sign-in isn't configured on this deployment yet (missing Supabase settings).",
  auth_link_expired: "That link has expired or was already used. Request a new one.",
  auth_callback_failed: "We couldn't complete sign-in. Please try again.",
};

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const [formError, setFormError] = useState<string | null>(
    URL_ERRORS[params.get("error") ?? ""] ?? null,
  );
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginValues) {
    setFormError(null);
    const { error } = await getSupabase().auth.signInWithPassword(values);
    if (error) {
      setFormError(friendlyAuthError(error.code, error.message));
      return;
    }
    router.replace(next);
    router.refresh();
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to continue learning."
      footer={
        <>
          New to Cognexa?{" "}
          <Link href="/signup" className={linkClass}>
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {formError && <FormMessage tone="error">{formError}</FormMessage>}
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
          autoComplete="current-password"
          error={errors.password}
          labelAction={
            <Link href="/forgot-password" className={`text-xs ${linkClass}`}>
              Forgot password?
            </Link>
          }
          {...register("password")}
        />
        <Button type="submit" className="h-9 w-full" disabled={isSubmitting}>
          {isSubmitting && <Loader2 aria-hidden className="animate-spin" />}
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <Divider />
      <GoogleButton next={next} onError={setFormError} />
    </AuthShell>
  );
}
