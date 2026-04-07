import type { ActionPayload, Observation, StepLog, TaskMeta } from "../types";

const headers = {
  "Content-Type": "application/json",
};

const handle = async <T>(res: Response): Promise<T> => {
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || res.statusText);
  }
  return res.json() as Promise<T>;
};

export const getTasks = async (): Promise<TaskMeta[]> => {
  const res = await fetch("/api/tasks");
  const data = await handle<{ tasks: TaskMeta[] }>(res);
  return data.tasks;
};

export const resetEnv = async (task: string): Promise<Observation> => {
  const res = await fetch("/api/reset", {
    method: "POST",
    headers,
    body: JSON.stringify({ task_difficulty: task }),
  });
  return handle<Observation>(res);
};

export const getState = async (): Promise<Observation> => {
  const res = await fetch("/api/state");
  return handle<Observation>(res);
};

export const stepEnv = async (
  action: ActionPayload,
  task?: string,
): Promise<Observation> => {
  const res = await fetch("/api/step", {
    method: "POST",
    headers,
    body: JSON.stringify({ action, task_difficulty: task }),
  });
  return handle<Observation>(res);
};

export const runAgent = async (params: {
  task_difficulty: string;
  model: string;
  base_url?: string;
  api_key?: string;
  max_steps?: number;
}): Promise<{ final_score: number; steps: StepLog[] }> => {
  const res = await fetch("/api/run-agent", {
    method: "POST",
    headers,
    body: JSON.stringify(params),
  });
  return handle<{ final_score: number; steps: StepLog[] }>(res);
};
