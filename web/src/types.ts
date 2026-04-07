export type Observation = {
  dom_state: Record<string, any>;
  task_description: string;
  current_score: number;
  feedback: string;
  done: boolean;
  reward?: number;
  metadata?: Record<string, any>;
};

export type ActionPayload = {
  action_type: "update_attribute" | "modify_css" | "reorder_nodes";
  node_id: string;
  attr_name?: string | null;
  new_value?: string | null;
  css_property?: string | null;
  new_hex_code?: string | null;
  new_child_order?: string[];
};

export type TaskMeta = { id: string; label: string; description: string };

export type StepLog = {
  step: number;
  action: ActionPayload;
  score: number;
  feedback: string;
};
