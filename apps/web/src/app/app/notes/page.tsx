import type { Metadata } from "next";

import { NotesPage } from "@/components/notes/notes-page";

export const metadata: Metadata = { title: "Notes" };

export default function Page() {
  return <NotesPage />;
}
