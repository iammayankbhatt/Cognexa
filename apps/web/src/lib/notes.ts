"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface NoteItem {
  concept_id: string;
  name: string;
  cluster: string;
  body: string;
  bookmarked: boolean;
  updated_at: string;
}

export interface RevisionSheet {
  id: string;
  subject_id: string;
  concept_ids: string[];
  content: string;
  created_at: string;
  citations?: string[];
  names?: Record<string, string>;
}

export function useNotes(filters: { q: string; cluster: string; bookmarked: boolean }) {
  return useQuery({
    queryKey: ["notes", filters],
    queryFn: () => {
      const p = new URLSearchParams();
      if (filters.q.trim()) p.set("q", filters.q.trim());
      if (filters.cluster !== "all") p.set("cluster", filters.cluster);
      if (filters.bookmarked) p.set("bookmarked", "true");
      return api<{ items: NoteItem[]; total: number }>(`/notes?${p}`);
    },
  });
}

export function useNoteMutations() {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["notes"] });
    void qc.invalidateQueries({ queryKey: ["note"] });
    void qc.invalidateQueries({ queryKey: ["dashboard"] });
  };
  const save = useMutation({
    mutationFn: ({
      conceptId,
      ...body
    }: {
      conceptId: string;
      body?: string;
      bookmarked?: boolean;
    }) => api(`/notes/${conceptId}`, { method: "PUT", body }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (conceptId: string) => api<void>(`/notes/${conceptId}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
  return { save, remove };
}

export function useSheets() {
  return useQuery({
    queryKey: ["revision-sheets"],
    queryFn: () => api<{ items: RevisionSheet[]; total: number }>("/revision-sheets"),
  });
}

export function useSheet(id: string) {
  return useQuery({
    queryKey: ["revision-sheets", id],
    queryFn: () => api<RevisionSheet>(`/revision-sheets/${id}`),
  });
}

export function useSheetMutations() {
  const qc = useQueryClient();
  const create = useMutation({
    mutationFn: (conceptIds?: string[]) =>
      api<RevisionSheet>("/revision-sheets", {
        method: "POST",
        body: conceptIds?.length ? { concept_ids: conceptIds } : {},
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["revision-sheets"] });
      void qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/revision-sheets/${id}`, { method: "DELETE" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["revision-sheets"] }),
  });
  return { create, remove };
}

/** A safe file name for a downloaded sheet. */
export function sheetFileName(sheet: Pick<RevisionSheet, "content" | "created_at">): string {
  const title =
    sheet.content
      .split("\n")
      .find((l) => l.trim())
      ?.replace(/^#+\s*/, "") ?? "revision-sheet";
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
  return `${slug || "revision-sheet"}-${sheet.created_at.slice(0, 10)}.md`;
}
