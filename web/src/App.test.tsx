import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./lib/api", () => {
  const mockObs = {
    dom_state: { id: "root", type: "div", children: [] },
    task_description: "mock",
    current_score: 0,
    feedback: "ok",
    done: false,
  };
  return {
    getTasks: vi.fn().mockResolvedValue([
      { id: "easy", label: "Easy", description: "desc" },
    ]),
    resetEnv: vi.fn().mockResolvedValue(mockObs),
    getState: vi.fn().mockResolvedValue(mockObs),
    stepEnv: vi.fn().mockResolvedValue({ ...mockObs, current_score: 0.5 }),
    runAgent: vi.fn().mockResolvedValue({ final_score: 1, steps: [] }),
  };
});

describe("App", () => {
  it("renders control rail and dom view", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText(/Control Rail/)).toBeInTheDocument());
    expect(screen.getByText(/DOM Visualizer/)).toBeInTheDocument();
  });
});
