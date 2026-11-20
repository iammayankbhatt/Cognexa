"use client";

import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { api, type Me } from "@/lib/api";
import { getSupabase } from "@/lib/supabase/client";
import { useHydrated } from "@/lib/use-hydrated";

export const ME_KEY = ["me"] as const;

/**
 * The signed-in user's profile, role, theme and today's AI usage (GET /me).
 * Reports "pending" until hydration has finished, so pages render the same skeleton as the
 * server even when the app shell already fetched /me (BUG-026).
 */
export function useMe(): UseQueryResult<Me> {
  const query = useQuery({ queryKey: ME_KEY, queryFn: () => api<Me>("/me"), staleTime: 60_000 });
  const hydrated = useHydrated();
  if (hydrated) return query;
  return {
    ...query,
    data: undefined,
    isPending: true,
    isSuccess: false,
    status: "pending",
  } as UseQueryResult<Me>;
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
