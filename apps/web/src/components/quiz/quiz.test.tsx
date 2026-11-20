import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { codeBlocks } from "@/components/learn/concept-page";
import { lockHints } from "@/components/learn/learn-library";
import { FeedbackPanel } from "@/components/quiz/feedback-panel";
import { describeAnswer, QuestionView } from "@/components/quiz/question-view";
import { ScoreRing } from "@/components/quiz/quiz-results";
import { isAnswered } from "@/lib/quiz/use-quiz";
import type { QuizQuestion } from "@/lib/quiz/types";

const mcq: QuizQuestion = {
  id: "stack-q01",
  concept_id: "stack",
  concept_name: "Stack",
  type: "mcq",
  difficulty: 1,
  prompt: "Which order does a stack use?",
  code: null,
  language: "python",
  options: [
    { id: "a", text: "FIFO" },
    { id: "b", text: "LIFO" },
    { id: "c", text: "Random" },
    { id: "d", text: "Sorted" },
  ],
  answer: null,
};
const multi: QuizQuestion = { ...mcq, id: "stack-q05", type: "multi_select" };

describe("answers", () => {
  it("describes answers in words", () => {
    expect(describeAnswer(mcq, "b")).toBe("LIFO");
    expect(describeAnswer(multi, ["a", "b"])).toBe("FIFO; LIFO");
    expect(describeAnswer({ ...mcq, type: "true_false" }, false)).toBe("False");
    expect(describeAnswer(mcq, null)).toBe("No answer");
    expect(describeAnswer({ ...mcq, type: "code_output" }, "1 2")).toBe("1 2");
  });

  it("knows when something is answered", () => {
    expect([null, undefined, "", "  ", []].map(isAnswered)).toEqual([
      false,
      false,
      false,
      false,
      false,
    ]);
    expect([false, "x", ["a"]].map(isAnswered)).toEqual([true, true, true]);
  });
});

describe("QuestionView", () => {
  it("selects one option for mcq and toggles options for multi-select", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender } = render(
      <QuestionView question={mcq} value={undefined} onChange={onChange} />,
    );
    await user.click(screen.getByRole("radio", { name: /LIFO/ }));
    expect(onChange).toHaveBeenLastCalledWith("b");
    rerender(<QuestionView question={multi} value={["a"]} onChange={onChange} />);
    await user.click(screen.getByRole("checkbox", { name: /LIFO/ }));
    expect(onChange).toHaveBeenLastCalledWith(["a", "b"]);
    await user.click(screen.getByRole("checkbox", { name: /FIFO/ }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("locks inputs and marks right and wrong options once graded", () => {
    render(
      <QuestionView
        question={mcq}
        value="a"
        onChange={() => undefined}
        graded={{
          question_id: "stack-q01",
          response: "a",
          score: 0,
          is_correct: false,
          correct_answer: "b",
        }}
      />,
    );
    expect(screen.getByRole("radio", { name: /FIFO/ })).toBeDisabled();
    expect(screen.getByLabelText("incorrect")).toBeInTheDocument();
  });
});

describe("FeedbackPanel", () => {
  it("shows the verdict, the correct answer and prerequisite actions", () => {
    render(
      <FeedbackPanel
        question={mcq}
        prereqName="Function Calls & the Call Stack"
        answer={{
          question_id: "stack-q01",
          response: "a",
          score: 0,
          is_correct: false,
          correct_answer: "b",
          feedback: "A stack is last in, first out.",
          diagnoses_prereq: "call_stack",
        }}
      />,
    );
    expect(screen.getByText("Not quite")).toBeInTheDocument();
    expect(screen.getByText("LIFO")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Learn Function Calls/ })).toHaveAttribute(
      "href",
      "/app/learn/call_stack",
    );
    expect(screen.getByRole("link", { name: /Ask the tutor/ }).getAttribute("href")).toMatch(
      /^\/app\/tutor\?ask=/,
    );
  });

  it("shows partial credit and pending grading", () => {
    const { rerender } = render(
      <FeedbackPanel
        question={multi}
        answer={{ question_id: "x", response: ["a"], score: 0.5, is_correct: false }}
      />,
    );
    expect(screen.getByText("Partly correct (50%)")).toBeInTheDocument();
    rerender(
      <FeedbackPanel
        question={multi}
        answer={{ question_id: "x", response: "t", pending: true, score: null }}
      />,
    );
    expect(screen.getByText("Grading pending")).toBeInTheDocument();
  });
});

describe("learn helpers", () => {
  it("splits a code section into language tabs", () => {
    const text =
      "Intro\n\n```python\ndef f():\n    pass\n```\n\nThen C++:\n\n```cpp\nint f() {}\n```\n";
    expect(codeBlocks(text)).toEqual([
      { lang: "python", code: "def f():\n    pass" },
      { lang: "cpp", code: "int f() {}" },
    ]);
  });

  it("hints at prerequisites the student has not reached yet", () => {
    const edges = [
      { source: "call_stack", target: "recursion", type: "PREREQUISITE_OF" },
      { source: "functions", target: "recursion", type: "PREREQUISITE_OF" },
      { source: "recursion", target: "backtracking", type: "RELATED_TO" },
    ];
    const names = new Map([
      ["call_stack", "Call Stack"],
      ["functions", "Functions"],
    ]);
    expect(lockHints("recursion", edges, new Map([["functions", 0.8]]), names)).toEqual([
      "Call Stack",
    ]);
    expect(lockHints("backtracking", edges, new Map(), names)).toEqual([]);
  });

  it("labels the score ring", () => {
    render(<ScoreRing ratio={0.75} label="Score 75 percent" />);
    expect(screen.getByRole("img", { name: "Score 75 percent" })).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
  });
});
