"""Extract the Python / C++ snippets from concept notes and run them.

Every snippet in a note's Code section must be a complete, runnable program (it prints or asserts),
so the notes can never ship broken code. C++ is written as C++14 (the oldest compiler we support),
compiled and run with g++ when available, otherwise skipped with a note.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.content.notes import extract_code_blocks, parse_note_file
from app.graph.loader import subject_dir

TIMEOUT_S = 15


@dataclass
class Snippet:
    concept_id: str
    language: str  # python | cpp
    index: int
    code: str

    @property
    def filename(self) -> str:
        ext = "py" if self.language == "python" else "cpp"
        return f"{self.concept_id}_{self.index}.{ext}"


@dataclass
class SnippetResult:
    snippet: Snippet
    status: str  # passed | failed | skipped
    detail: str = ""


def collect_snippets(subject_id: str = "dsa", only: set[str] | None = None) -> list[Snippet]:
    out: list[Snippet] = []
    for path in sorted((subject_dir(subject_id) / "content").glob("*.md")):
        if only and path.stem not in only:
            continue
        note = parse_note_file(path)
        code = next((s.text for s in note.sections if s.kind == "code"), "")
        for lang in ("python", "cpp"):
            for i, block in enumerate(extract_code_blocks(code, lang), 1):
                out.append(Snippet(path.stem, lang, i, block))
    return out


def write_snippets(snippets: list[Snippet], directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for s in snippets:
        p = directory / s.filename
        p.write_text(s.code, encoding="utf-8")
        paths.append(p)
    return paths


def gpp() -> str | None:
    return shutil.which("g++")


def run_snippet(s: Snippet, directory: Path) -> SnippetResult:
    path = directory / s.filename
    if s.language == "python":
        try:
            r = subprocess.run(
                [sys.executable, "-I", str(path)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
                cwd=directory,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return SnippetResult(s, "failed", f"timed out after {TIMEOUT_S}s")
        if r.returncode != 0:
            return SnippetResult(s, "failed", (r.stderr or r.stdout)[-800:])
        return SnippetResult(s, "passed")

    compiler = gpp()
    if compiler is None:
        return SnippetResult(s, "skipped", "g++ not available")
    exe = directory / (path.stem + (".exe" if sys.platform == "win32" else ".out"))
    c = subprocess.run(
        [compiler, "-std=c++14", "-O0", "-Wall", "-o", str(exe), str(path)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=directory,
        check=False,
    )
    if c.returncode != 0:
        return SnippetResult(s, "failed", "compile error: " + c.stderr[-800:])
    try:
        r = subprocess.run(
            [str(exe)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            cwd=directory,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SnippetResult(s, "failed", f"timed out after {TIMEOUT_S}s")
    if r.returncode != 0:
        return SnippetResult(
            s, "failed", f"exit code {r.returncode}: {(r.stderr or r.stdout)[-600:]}"
        )
    return SnippetResult(s, "passed")


def run_all(snippets: list[Snippet], directory: Path, workers: int = 6) -> list[SnippetResult]:
    """Write and run all snippets, in parallel (each is an independent process)."""
    from concurrent.futures import ThreadPoolExecutor

    write_snippets(snippets, directory)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda sn: run_snippet(sn, directory), snippets))


@dataclass
class QuestionCodeResult:
    question_id: str
    status: str  # passed | failed | skipped
    detail: str = ""


def _normalise(output: str) -> str:
    return chr(10).join(line.rstrip() for line in output.strip().splitlines())


def verify_code_questions(
    subject_id: str, directory: Path, only: set[str] | None = None
) -> list[QuestionCodeResult]:
    """Run every code_output question's code and compare its stdout with the stored answer."""
    from app.content.loader import load_questions

    results: list[QuestionCodeResult] = []
    directory.mkdir(parents=True, exist_ok=True)
    for concept_id, q in load_questions(subject_id):
        if q.type != "code_output" or (only and concept_id not in only):
            continue
        assert q.code is not None and isinstance(q.answer, str)
        stem = q.id.replace("-", "_")
        if q.language == "python":
            path = directory / f"q_{stem}.py"
            path.write_text(q.code, encoding="utf-8")
            try:
                r = subprocess.run(
                    [sys.executable, "-I", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_S,
                    cwd=directory,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                results.append(QuestionCodeResult(q.id, "failed", "timed out"))
                continue
            got = r.stdout if r.returncode == 0 else f"[exit {r.returncode}] {r.stderr[-200:]}"
        else:
            compiler = gpp()
            if compiler is None:
                results.append(QuestionCodeResult(q.id, "skipped", "g++ not available"))
                continue
            path = directory / f"q_{stem}.cpp"
            path.write_text(q.code, encoding="utf-8")
            exe = directory / (f"q_{stem}" + (".exe" if sys.platform == "win32" else ".out"))
            c = subprocess.run(
                [compiler, "-std=c++14", "-O0", "-o", str(exe), str(path)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=directory,
                check=False,
            )
            if c.returncode != 0:
                results.append(
                    QuestionCodeResult(q.id, "failed", "compile error: " + c.stderr[-300:])
                )
                continue
            r = subprocess.run(
                [str(exe)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
                cwd=directory,
                check=False,
            )
            got = r.stdout if r.returncode == 0 else f"[exit {r.returncode}]"
        if _normalise(got) == _normalise(q.answer):
            results.append(QuestionCodeResult(q.id, "passed"))
        else:
            results.append(
                QuestionCodeResult(
                    q.id, "failed", f"expected {q.answer!r} but program printed {got!r}"
                )
            )
    return results
