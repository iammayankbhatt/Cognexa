"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { api, type Me } from "@/lib/api";
import { getSupabase } from "@/lib/supabase/client";

export const ME_KEY = ["me"] as const;

/** The signed-in user's profile, role, theme and today's AI usage (GET /me). */
export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: () => api<Me>("/me"), staleTime: 60_000 });
}

export function useSignOut() {
  const router = useRouter();
  const qc = useQueryClient();
  return useCallback(async () => {
    await getSupabase().auth.signOut();
    qc.clear();
    router.replace("/login");
    router.refresh();
  }, [router, qc]);
}
