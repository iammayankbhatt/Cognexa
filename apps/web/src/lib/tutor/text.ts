/**
 * Answer text helpers: [[concept_id]] citations and the <followups> trailer.
 *
 * The backend already strips the trailer from what it streams and stores; the client strips it
 * again defensively (older messages, partial streams) and never shows raw trailer text.
 */

const CITATION = /\[\[([a-z][a-z0-9_]{0,63})\]\]/g;
const TRAILER_OPEN = "<followups>";
export const CONCEPT_HREF_PREFIX = "#concept=";

/** Ids cited in the text, in order of first appearance (code is ignored). */
export function citedIds(markdown: string): string[] {
  const ids: string[] = [];
  for (const part of splitCode(markdown)) {
    if (part.code) continue;
    for (const m of part.text.matchAll(CITATION)) if (!ids.includes(m[1])) ids.push(m[1]);
  }
  return ids;
}

/**
 * Turn [[id]] into a Markdown link `[id](#concept=id)` that the renderer shows as a concept chip.
 * Text inside inline code and fenced code blocks is left alone.
 */
export function linkCitations(markdown: string): string {
  return splitCode(markdown)
    .map((p) => (p.code ? p.text : p.text.replace(CITATION, `[$1](${CONCEPT_HREF_PREFIX}$1)`)))
    .join("");
}

export function conceptIdFromHref(href: string | undefined): string | null {
  if (!href?.startsWith(CONCEPT_HREF_PREFIX)) return null;
  const id = href.slice(CONCEPT_HREF_PREFIX.length);
  return /^[a-z][a-z0-9_]{0,63}$/.test(id) ? id : null;
}

interface Part {
  text: string;
  code: boolean;
}

/** Split Markdown into code (fenced blocks, inline spans) and non-code parts. */
export function splitCode(markdown: string): Part[] {
  const parts: Part[] = [];
  const re = /(```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`[^`\n]*`)/g;
  let last = 0;
  for (const m of markdown.matchAll(re)) {
    const at = m.index ?? 0;
    if (at > last) parts.push({ text: markdown.slice(last, at), code: false });
    parts.push({ text: m[0], code: true });
    last = at + m[0].length;
  }
  if (last < markdown.length) parts.push({ text: markdown.slice(last), code: false });
  return parts;
}

/** Remove a <followups> trailer (complete or still streaming, or a partial opening tag). */
export function stripTrailer(text: string): string {
  const at = text.indexOf(TRAILER_OPEN);
  if (at >= 0) return text.slice(0, at).trimEnd();
  for (let n = Math.min(TRAILER_OPEN.length - 1, text.length); n > 0; n--) {
    if (TRAILER_OPEN.startsWith(text.slice(-n))) return text.slice(0, -n);
  }
  return text;
}

/** Follow-up questions from a trailer, if one is present (at most 2). */
export function parseTrailer(text: string): string[] {
  const m = /<followups>([\s\S]*?)(?:<\/followups>|$)/.exec(text);
  if (!m) return [];
  const body = m[1].trim();
  let items: string[] = [];
  try {
    const data: unknown = JSON.parse(body);
    if (Array.isArray(data)) items = data.map(String);
  } catch {
    const lines = body.split("\n").map((l) => l.replace(/^[\s\-*"']+|["'\s]+$/g, ""));
    const questions = lines.filter((l) => l.endsWith("?"));
    items = questions.length ? questions : lines;
  }
  return items
    .map((i) => i.replace(/\s+/g, " ").trim().slice(0, 200))
    .filter(Boolean)
    .slice(0, 2);
}
