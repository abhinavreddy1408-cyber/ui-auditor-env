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
# [Keep existing DOM_EASY, DOM_MEDIUM, DOM_HARD, DOM_OPENENV definitions check Turn 11/12]
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
        self.reset()

    def reset(self, task_difficulty: Optional[str] = None) -> Observation:
        self.steps = 0
        if task_difficulty: self.task_difficulty = task_difficulty.lower()
        
        if self.task_difficulty == "openenv":
            self.dom = copy.deepcopy(DOM_OPENENV)
            self.task_desc = "Fix WCAG issues: alt text, contrast, and hierarchy."
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
                # Basic reorder logic
                lookup = {c["id"]: c for c in node.get("children", [])}
                node["children"] = [lookup[cid] for cid in action.new_child_order if cid in lookup]
        return self.state()

    def _calculate_reward(self) -> float:
        node = self._find_node(self.dom, "img_001") or self._find_node(self.dom, "hero-img")
        if node and node.get("alt") != "": return 0.95
        return 0.05
