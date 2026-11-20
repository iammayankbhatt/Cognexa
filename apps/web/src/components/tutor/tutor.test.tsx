import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Markdown } from "@/components/tutor/markdown";
import { AssistantMessage } from "@/components/tutor/message-item";
import { QuickCheck } from "@/components/tutor/quick-check";
import { traceSubgraph } from "@/components/tutor/trace-graph";
import { TraceStrip } from "@/components/tutor/trace-strip";
import type { ChatMessage, RetrievalTrace } from "@/lib/tutor/types";

const trace: RetrievalTrace = {
  version: 1,
  mode: "graphrag",
  question: "Why does my recursive function crash?",
  is_on_topic: true,
  intent: "debug",
  classification_path: "llm",
  matched: [{ id: "recursion", name: "Recursion", confidence: 0.86, reason: "", source: "llm" }],
  fallback: null,
  depth: 2,
  concepts: [
    {
      id: "recursion",
      name: "Recursion",
      role: "matched",
      depth: 0,
      weak: null,
      mastery: null,
      path: [],
    },
    {
      id: "call_stack",
      name: "Call Stack",
      role: "prerequisite",
      depth: 1,
      weak: true,
      mastery: null,
      path: [{ source: "call_stack", target: "recursion", type: "PREREQUISITE_OF" }],
    },
    {
      id: "backtracking",
      name: "Backtracking",
      role: "related",
      depth: 1,
      weak: null,
      mastery: null,
      path: [{ source: "recursion", target: "backtracking", type: "RELATED_TO" }],
    },
  ],
  controller: [{ action: "answer_now", reason: "enough", question: null }],
  diagnostic: null,
  diagnostic_reply: null,
  chunks: [{ id: "c1", concept_id: "call_stack", kind: "overview", tokens: 120, score: null }],
  budget_tokens: 3000,
  used_tokens: 120,
  timings_ms: {},
  cached: false,
  truncated: false,
  citations: ["call_stack"],
  followups: [],
};

function assistant(over: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "m1",
    role: "assistant",
    content: "It crashes because of the [[call_stack]].",
    mode: "graphrag",
    status: "done",
    trace,
    followups: ["What is a stack frame?", "How deep can recursion go?"],
    feedback: null,
    diagnostic: false,
    truncated: false,
    cached: false,
    ...over,
  };
}

const noop = () => undefined;

describe("Markdown", () => {
  it("renders citations as concept chips linking to the concept page", () => {
    render(
      <Markdown
        text="See [[call_stack]] for details."
        conceptNames={{ call_stack: "Call Stack" }}
      />,
    );
    const chip = screen.getByRole("link", { name: "Call Stack" });
    expect(chip).toHaveAttribute("href", "/app/learn/call_stack");
  });

  it("never renders raw HTML from the answer", () => {
    const { container } = render(
      <Markdown text={'Hi <img src=x onerror="alert(1)"> <script>x</script>'} />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
  });

  it("shows fenced code with a language label and a copy button", () => {
    render(<Markdown text={"```python\ndef f():\n    return 1\n```"} />);
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy code" })).toBeInTheDocument();
  });

  it("renders math with KaTeX", () => {
    const { container } = render(<Markdown text="Cost is $O(n \\log n)$." />);
    expect(container.querySelector(".katex")).not.toBeNull();
  });
});

describe("TraceStrip", () => {
  it("shows the match, the graph walk and weak prerequisites", () => {
    const onOpen = vi.fn();
    render(<TraceStrip trace={trace} onOpen={onOpen} />);
    expect(screen.getByText("Recursion")).toBeInTheDocument();
    expect(screen.getByText("(0.86)")).toBeInTheDocument();
    expect(screen.getByText("walking prerequisites")).toBeInTheDocument();
    expect(screen.getByText("Call Stack")).toBeInTheDocument();
    expect(screen.getByText("weak")).toBeInTheDocument();
  });

  it("describes plain RAG and off-topic traces", () => {
    const { rerender } = render(<TraceStrip trace={{ ...trace, mode: "plain_rag" }} />);
    expect(screen.getByText(/Plain RAG: 1 chunks/)).toBeInTheDocument();
    rerender(<TraceStrip trace={{ ...trace, is_on_topic: false }} />);
    expect(screen.getByText("Not a DSA question")).toBeInTheDocument();
  });
});

describe("trace subgraph", () => {
  it("contains the recorded concepts and exact edges", () => {
    const { nodes, edges } = traceSubgraph(trace);
    expect(nodes.map((n) => n.id).sort()).toEqual(["backtracking", "call_stack", "recursion"]);
    expect(edges).toContainEqual({
      source: "call_stack",
      target: "recursion",
      type: "PREREQUISITE_OF",
    });
  });
});

describe("AssistantMessage", () => {
  it("offers follow-ups and feedback actions on the latest answer", async () => {
    const user = userEvent.setup();
    const onFollowup = vi.fn();
    const onRate = vi.fn();
    const onReport = vi.fn();
    render(
      <AssistantMessage
        message={assistant()}
        names={{ call_stack: "Call Stack" }}
        isLatest
        busy={false}
        quickCheckActive={false}
        onFollowup={onFollowup}
        onRegenerate={noop}
        onRate={onRate}
        onReport={onReport}
        onWhy={noop}
        onQuickCheckAnswer={noop}
      />,
    );
    await user.click(screen.getByRole("button", { name: "What is a stack frame?" }));
    expect(onFollowup).toHaveBeenCalledWith("What is a stack frame?");
    await user.click(screen.getByRole("button", { name: "Helpful" }));
    expect(onRate).toHaveBeenCalledWith(1);
    await user.click(screen.getByRole("button", { name: "Report answer" }));
    expect(onReport).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Regenerate" })).toBeInTheDocument();
  });

  it("shows a reported answer with a flag and clears a thumb on second click", async () => {
    const user = userEvent.setup();
    const onRate = vi.fn();
    render(
      <AssistantMessage
        message={assistant({ feedback: { rating: 1, reported: true } })}
        names={{}}
        isLatest={false}
        busy={false}
        quickCheckActive={false}
        onFollowup={noop}
        onRegenerate={noop}
        onRate={onRate}
        onReport={noop}
        onWhy={noop}
        onQuickCheckAnswer={noop}
      />,
    );
    expect(screen.getByText("Reported for review")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reported" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Regenerate" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Helpful" }));
    expect(onRate).toHaveBeenCalledWith(0);
  });

  it("hides trailer text while streaming", () => {
    render(
      <AssistantMessage
        message={assistant({ status: "streaming", content: 'Partial answer <followups>["x' })}
        names={{}}
        isLatest
        busy
        quickCheckActive={false}
        onFollowup={noop}
        onRegenerate={noop}
        onRate={noop}
        onReport={noop}
        onWhy={noop}
        onQuickCheckAnswer={noop}
      />,
    );
    expect(screen.getByText("Partial answer")).toBeInTheDocument();
    expect(screen.queryByText(/followups/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Helpful" })).toBeNull();
  });
});

describe("QuickCheck", () => {
  it("collects an answer only while active", async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    const { rerender } = render(
      <QuickCheck question="Quick check: what does each call push?" active onAnswer={onAnswer} />,
    );
    expect(screen.getByText("what does each call push?")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Your answer"), "a stack frame{Enter}");
    expect(onAnswer).toHaveBeenCalledWith("a stack frame");
    rerender(<QuickCheck question="Quick check: x?" active={false} onAnswer={onAnswer} />);
    expect(screen.queryByLabelText("Your answer")).toBeNull();
  });
});
