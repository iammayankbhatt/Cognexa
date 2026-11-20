import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConceptChip } from "./concept-chip";
import { EmptyState } from "./empty-state";
import { ErrorState } from "./error-state";
import { LoadingSkeleton } from "./loading-skeleton";
import { masteryLevel } from "./mastery";
import { MasteryBadge } from "./mastery-badge";
import { PageHeader } from "./page-header";
import { StatCard } from "./stat-card";

describe("masteryLevel", () => {
  it.each([
    [0, "low"],
    [0.39, "low"],
    [0.4, "mid"],
    [0.74, "mid"],
    [0.75, "mid"], // BUG-030: the backend calls exactly 0.75 "developing"
    [0.76, "high"],
    [1, "high"],
  ])("maps %s to %s", (value, level) => {
    expect(masteryLevel(value)).toBe(level);
  });
});

describe("MasteryBadge", () => {
  it("shows level and percentage", () => {
    render(<MasteryBadge value={0.82} />);
    expect(screen.getByText("Strong")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("clamps out-of-range and NaN values", () => {
    const { rerender, container } = render(<MasteryBadge value={5} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    rerender(<MasteryBadge value={Number.NaN} />);
    expect(container.firstElementChild).toHaveAttribute("data-level", "low");
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("can hide the value", () => {
    render(<MasteryBadge value={0.5} showValue={false} />);
    expect(screen.queryByText("50%")).not.toBeInTheDocument();
  });
});

describe("ConceptChip", () => {
  it("renders a link when href is set", () => {
    render(<ConceptChip name="Recursion" href="/app/learn/recursion" />);
    expect(screen.getByRole("link", { name: /Recursion/ })).toHaveAttribute(
      "href",
      "/app/learn/recursion",
    );
  });

  it("renders plain text with relation and mastery dot", () => {
    render(<ConceptChip name="Call Stack" relation="prerequisite" mastery={0.2} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText(/Prerequisite/)).toBeInTheDocument();
    expect(screen.getByTestId("mastery-dot").className).toContain("bg-danger");
  });
});

describe("PageHeader / StatCard / EmptyState", () => {
  it("renders header title, description and actions", () => {
    render(
      <PageHeader title="Progress" description="Your mastery" actions={<button>Go</button>} />,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Progress" })).toBeInTheDocument();
    expect(screen.getByText("Your mastery")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });

  it("renders a stat card", () => {
    render(<StatCard label="Streak" value="7" hint="Best: 12" />);
    expect(screen.getByText("Streak")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("Best: 12")).toBeInTheDocument();
  });

  it("renders an empty state with an action", () => {
    render(<EmptyState title="Nothing here" description="Add one" action={<button>Add</button>} />);
    expect(screen.getByRole("heading", { name: "Nothing here" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("is an alert, shows the request id, and retries", async () => {
    const onRetry = vi.fn();
    render(<ErrorState requestId="abc123" onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("hides retry when no handler is given", () => {
    render(<ErrorState />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

describe("LoadingSkeleton", () => {
  it("announces itself as busy", () => {
    render(<LoadingSkeleton variant="list" label="Loading concepts" />);
    const el = screen.getByRole("status", { name: "Loading concepts" });
    expect(el).toHaveAttribute("aria-busy", "true");
  });
});
