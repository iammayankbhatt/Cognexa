import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { DesignShowcase } from "./showcase";

export const metadata: Metadata = { title: "Design reference", robots: { index: false } };

/** Dev-only visual reference. Returns 404 in production builds. */
export default function DesignPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <DesignShowcase />;
}
