"""Document splitting for ingestion (pure functions, no services)."""

from __future__ import annotations

from app.admin.llm_proposals import extract_text, split_sections
from tests.pdf_helpers import make_pdf

BODY = (
    "This paragraph explains the idea in enough words to be a real section of lecture notes, "
    "with a definition, a short example and the reason it matters for later topics in the course. "
    "Sections shorter than the minimum size are merged into the next one, so this text is long."
)


def page(title: str) -> list[str]:
    words = BODY.split()
    return [title] + [" ".join(words[i : i + 12]) for i in range(0, len(words), 12)]


def test_bare_title_lines_in_a_pdf_start_sections() -> None:
    """BUG-036: a 6-page PDF with plain page titles used to come out as one section."""
    titles = ["Recursion", "Call Stack", "Binary Search", "Hash Table", "Breadth-First Search",
              "Merge Sort"]  # fmt: skip
    doc = extract_text("notes.pdf", make_pdf([page(t) for t in titles]))
    sections = split_sections(doc.text)
    assert [s.heading for s in sections] == titles
    assert all("lecture notes" in s.text for s in sections)
    assert [s.index for s in sections] == list(range(6))


def test_short_last_line_of_a_paragraph_is_not_a_title() -> None:
    text = (
        f"Stacks\n{BODY}\nwith LIFO order\n\n{BODY}\n\nPeek Operation\n{BODY} The peek operation "
        "reads the top without removing it."
    )
    sections = split_sections(text)
    assert [s.heading for s in sections] == ["Stacks", "Peek Operation"]
    assert "with LIFO order" in sections[0].text


def test_code_and_sentences_are_not_titles() -> None:
    text = (
        f"Factorial\n{BODY}\n\ndef fact(n):\n    return 1 if n == 0 else n * fact(n - 1)\n\n"
        f"It works.\n{BODY}\n\nTwo Titles In A Row\nAnother Title Line\n{BODY}"
    )
    headings = [s.heading for s in split_sections(text)]
    assert "def fact(n):" not in headings and "It works." not in headings
    # a title followed directly by another title-shaped line: only the second one starts a block
    assert "Two Titles In A Row" not in headings


def test_markdown_and_numbered_headings_still_win() -> None:
    text = f"# Stacks\n\n{BODY}\n\n3.2 Queues and deques\n{BODY}"
    assert [s.heading for s in split_sections(text)] == ["Stacks", "3.2 Queues and deques"]


def test_form_feed_page_breaks_count_as_blank_lines() -> None:
    text = f"Heaps\n{BODY}\fTries\n{BODY}"
    assert [s.heading for s in split_sections(text)] == ["Heaps", "Tries"]
