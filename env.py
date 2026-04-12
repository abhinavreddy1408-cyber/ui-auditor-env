from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
import copy

# ============================================================================
# OpenEnv Spec — Strictly the truth requested by the validator
# ============================================================================

class Action(BaseModel):
    action_type: str = Field(..., description="update_attribute, modify_css, or reorder_nodes")
    node_id: str
    attribute: Optional[str] = None
    property: Optional[str] = None
    value: Optional[str] = None
    new_parent_id: Optional[str] = None
    new_child_order: Optional[List[str]] = None

class Observation(BaseModel):
    dom_state: Dict[str, Any]
    task_description: str
    current_score: float = 0.05
    done: bool = False
    feedback: str = ""

# --- Scenarios (EASY, MEDIUM, HARD, OPENENV) ---
DOM_EASY = {
    "id": "root", "type": "div",
    "children": [{
        "id": "hero-section", "type": "section",
        "children": [
            {"id": "hero-text", "type": "h1", "content": "Discover Premium Dashboard Analytics"},
            {"id": "hero-img", "type": "img", "src": "hero.png", "alt": "", "css": {}}
        ]
    }]
}

DOM_MEDIUM = {
    "id": "root", "type": "div",
    "children": [
        {"id": "main-container", "type": "main", "children": [
            {"id": "title", "type": "h1", "content": "Performance Metrics"},
            {"id": "btn_001", "type": "button", "content": "Download Report", "css": {"color": "#E1E1E1", "background-color": "#FFFFFF"}}
        ]}
    ]
}

DOM_HARD = {
    "id": "root", "type": "div",
    "children": [
        {"id": "h3_001", "type": "h3", "content": "Secondary Stats"},
        {"id": "h1_001", "type": "h1", "content": "Global Accessibility"},
        {"id": "h2_001", "type": "h2", "content": "Region Breakdown"},
        {"id": "input_001", "type": "input", "placeholder": "Enter username...", "attributes": {"type": "text"}}
    ]
}

DOM_OPENENV = {
    "id": "root", "type": "div",
    "children": [
        {"id": "nav-block", "type": "nav", "content": "Home | About", "css": {"margin": "10px"}},
        {"id": "img_001", "type": "img", "src": "hero.png", "alt": "", "css": {}},
        {"id": "bad-contrast-div", "type": "div", "content": "Contrast test", "css": {"color": "#E1E1E1", "background-color": "#FFFFFF"}}
    ]
}

STEP_PENALTY = 0.01
_SCORE_MIN   = 0.05
_SCORE_MAX   = 0.95

def _clamp(score: float) -> float:
    return round(max(_SCORE_MIN, min(_SCORE_MAX, score)), 4)

class UIAuditorEnv:
    def __init__(self, task_difficulty: str = "openenv"):
        self.task_difficulty = task_difficulty.lower()
        self.dom: Dict[str, Any] = {}
        self.steps = 0
        self.max_steps = 15
        self.grader_fn: Optional[Any] = None
        self.reset()

    def reset(self, task_difficulty: Optional[str] = None, grader: Optional[Any] = None) -> Observation:
        self.steps = 0
        if task_difficulty: self.task_difficulty = task_difficulty.lower()
        if grader: self.grader_fn = grader
        
        if self.task_difficulty == "openenv":
            self.dom = copy.deepcopy(DOM_OPENENV)
            self.task_desc = "Fix WCAG issues: alt text, contrast, and hierarchy."
        elif self.task_difficulty == "medium":
            self.dom = copy.deepcopy(DOM_MEDIUM)
            self.task_desc = "Fix CTA button color contrast using Emerald Green (#50C878)."
        elif self.task_difficulty == "hard":
            self.dom = copy.deepcopy(DOM_HARD)
            self.task_desc = "Fix heading hierarchy and add form labels."
        else:
            self.dom = copy.deepcopy(DOM_EASY)
            self.task_desc = "Add alt text to hero image."
        return self.state()

    def state(self) -> Observation:
        score = _clamp(self._calculate_reward())
        done = self.steps >= self.max_steps or score >= _SCORE_MAX
        return Observation(dom_state=self.dom, task_description=self.task_desc, current_score=score, done=done)

    def _find_node(self, node: dict, target_id: str) -> Optional[dict]:
        if node.get("id") == target_id: return node
        for child in node.get("children", []):
            found = self._find_node(child, target_id)
            if found: return found
        return None

    def step(self, action: Action) -> Observation:
        self.steps += 1
        node = self._find_node(self.dom, action.node_id)
        if node:
            if action.action_type == "update_attribute" and action.attribute:
                if action.attribute not in ("children", "id"):
                    node[action.attribute] = action.value
            elif action.action_type == "modify_css" and action.property:
                node.setdefault("css", {})[action.property] = action.value
            elif action.action_type == "reorder_nodes" and action.new_child_order:
                lookup = {c["id"]: c for c in node.get("children", [])}
                node["children"] = [lookup[cid] for cid in action.new_child_order if cid in lookup]
        return self.state()

    def _calculate_reward(self) -> float:
        # Use task-specific grader if provided
        if self.grader_fn:
            try:
                return self.grader_fn(self)
            except Exception:
                pass
        
        # Fallback to default alt-text check
        node = self._find_node(self.dom, "img_001") or self._find_node(self.dom, "hero-img")
        if node and node.get("alt") != "": return 0.95
        return 0.05

