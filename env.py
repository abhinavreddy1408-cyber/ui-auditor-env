from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
import copy

# ============================================================================
# OpenEnv Spec — Strictly typed Pydantic models & pure dictionary DOM
#
# FIX: Phase 2 deep validation requires each task grader score to be
#      STRICTLY between 0 and 1 (score > 0.0 AND score < 1.0).
#      We satisfy this by clamping all scores to [0.05, 0.95].
#        - Initial (broken) DOM  → 0.05
#        - Perfect fix           → 0.95
#      This keeps every returned score strictly inside (0, 1).
# ============================================================================

class Action(BaseModel):
    action_type: str = Field(..., description="One of: 'update_attribute', 'modify_css', 'reorder_nodes'")
    node_id: str = Field(..., description="The ID of the DOM node to act upon")
    attr_name: Optional[str] = Field(None, description="Attribute name for update_attribute")
    new_value: Optional[str] = Field(None, description="New value for update_attribute")
    css_property: Optional[str] = Field(None, description="CSS property for modify_css")
    new_hex_code: Optional[str] = Field(None, description="New hex code for modify_css")
    new_child_order: Optional[List[str]] = Field(None, description="List of child IDs for reorder_nodes")

class Observation(BaseModel):
    dom_state: Dict[str, Any] = Field(..., description="Pure Python dictionary representing the DOM")
    task_description: str = Field(..., description="Instructions for the current task")
    current_score: float = Field(0.05, description="Current dense reward score, strictly in (0, 1)")
    is_done: bool = Field(False, description="Whether the episode has ended")
    feedback: str = Field(..., description="Feedback from the last action or current status")

class RewardModel(BaseModel):
    score: float = Field(..., description="Dense reward strictly between 0 and 1")
    is_terminal: bool = Field(..., description="True if episode is over")

# --- DOM Scenarios ---

DOM_EASY = {
    "id": "root", "type": "div",
    "children": [{
        "id": "hero-section", "type": "section",
        "children": [
            {"id": "hero-text", "type": "h1", "content": "Discover Premium Dashboard Analytics"},
            {"id": "hero-img", "type": "img",
             "src": "/assets/hero-dribbble-mockup.png",
             "alt": "",
             "css": {"border-radius": "12px", "box-shadow": "0 4px 12px rgba(0,0,0,0.15)", "border": "1px solid #FFD700"}}
        ]
    }]
}

DOM_MEDIUM = {
    "id": "root", "type": "div",
    "children": [{
        "id": "cta-container", "type": "div",
        "css": {"padding": "40px", "background-color": "#FFFFFF"},
        "children": [{
            "id": "upgrade-btn", "type": "button", "content": "Upgrade to Pro",
            "css": {"background-color": "#FFFFFF", "color": "#E0F2E9",
                    "border-radius": "8px", "padding": "12px 24px",
                    "font-family": "Inter, sans-serif", "font-weight": "600"}
        }]
    }]
}

DOM_HARD = {
    "id": "root", "type": "div",
    "children": [{
        "id": "header-chaotic", "type": "div",
        "children": [
            {"id": "sub-subtitle", "type": "div",  "content": "Overview metrics & active users"},
            {"id": "main-title",   "type": "h2",   "content": "Dashboard Homepage",
             "css": {"color": "#50C878", "font-weight": "bold"}},
            {"id": "subtitle",     "type": "h3",   "content": "User Growth Trends"}
        ]
    }]
}

STEP_PENALTY = 0.01
_SCORE_MIN   = 0.05   # strictly > 0
_SCORE_MAX   = 0.95   # strictly < 1


def _clamp(score: float) -> float:
    return round(max(_SCORE_MIN, min(_SCORE_MAX, score)), 4)


class UIAuditorEnv:
    def __init__(self, task_difficulty: str = "easy"):
        self.task_difficulty = task_difficulty.lower()
        self.dom: Dict[str, Any] = {}
        self.steps = 0
        self.max_steps = 15
        self.reset()

    def reset(self, task_difficulty: Optional[str] = None) -> Observation:
        self.steps = 0
        if task_difficulty:
            self.task_difficulty = task_difficulty.lower()

        if self.task_difficulty == "easy":
            self.dom = copy.deepcopy(DOM_EASY)
            self.task_desc = (
                "Accessibility Fix: Find the hero image (id: 'hero-img') missing its "
                "'alt' text and add a descriptive one about a premium dashboard."
            )
        elif self.task_difficulty == "medium":
            self.dom = copy.deepcopy(DOM_MEDIUM)
            self.task_desc = (
                "WCAG Compliance Fix: Fix the CTA button (id: 'upgrade-btn') color "
                "contrast. Change its CSS 'color' to emerald green ('#50C878')."
            )
        elif self.task_difficulty == "hard":
            self.dom = copy.deepcopy(DOM_HARD)
            self.task_desc = (
                "Semantic Structuring: In 'header-chaotic', change main-title to h1, "
                "subtitle to h2, sub-subtitle to h3, then reorder: "
                "[main-title, subtitle, sub-subtitle]."
            )
        else:
            raise ValueError("task_difficulty must be 'easy', 'medium', or 'hard'")
        return self.state()

    def state(self) -> Observation:
        score = _clamp(self._calculate_reward())
        is_done = self.steps >= self.max_steps
        if is_done:
            feedback = f"Episode over after {self.steps} steps. Final score: {score}."
        else:
            feedback = f"Score: {round(score*100,1)}% — keep fixing UI issues (target: 95%)."
        return Observation(
            dom_state=self.dom,
            task_description=self.task_desc,
            current_score=score,
            is_done=is_done,
            feedback=feedback,
        )

    def _find_node(self, node: dict, target_id: str) -> Optional[dict]:
        if node.get("id") == target_id:
            return node
        for child in node.get("children", []):
            found = self._find_node(child, target_id)
            if found:
                return found
        return None

    def step(self, action: Action) -> Tuple[Observation, RewardModel, bool, dict]:
        self.steps += 1
        score_before = _clamp(self._calculate_reward())
        info: Dict[str, Any] = {
            "step": self.steps,
            "action_type": action.action_type,
            "node_id": action.node_id,
            "score_before": score_before,
            "penalty": 0.0,
            "reason": "ok",
        }

        node = self._find_node(self.dom, action.node_id)
        if not node:
            obs = self.state()
            penalized = _clamp(obs.current_score - STEP_PENALTY)
            obs.current_score = penalized
            obs.feedback = f"Node '{action.node_id}' not found — penalty applied. Score: {penalized}"
            info.update({"penalty": STEP_PENALTY, "reason": "node_not_found", "score_after": penalized})
            return obs, RewardModel(score=penalized, is_terminal=obs.is_done), obs.is_done, info

        if action.action_type == "update_attribute":
            if action.attr_name and action.new_value is not None:
                if action.attr_name not in ("content", "id"):
                    node[action.attr_name] = action.new_value

        elif action.action_type == "modify_css":
            if action.css_property and action.new_hex_code is not None:
                node.setdefault("css", {})[action.css_property] = action.new_hex_code

        elif action.action_type == "reorder_nodes":
            if action.new_child_order and "children" in node:
                lookup = {c["id"]: c for c in node["children"]}
                ordered = [lookup[cid] for cid in action.new_child_order if cid in lookup]
                extras = [c for c in node["children"] if c["id"] not in set(action.new_child_order)]
                node["children"] = ordered + extras

        obs = self.state()
        score_after = obs.current_score

        if score_after <= score_before:
            penalized = _clamp(score_after - STEP_PENALTY)
            obs.current_score = penalized
            obs.feedback += f" (No progress — penalty {STEP_PENALTY} applied.)"
            info.update({"penalty": STEP_PENALTY, "reason": "no_progress"})
            score_after = penalized

        info["score_after"] = score_after
        return obs, RewardModel(score=score_after, is_terminal=obs.is_done), obs.is_done, info

    def _calculate_reward(self) -> float:
        """
        Raw reward in [0.0, 1.0] before clamping to (0.05, 0.95).
        Scoring:
          Easy   : 0.0 (no alt) → 0.5 (weak alt) → 1.0 (descriptive alt)
          Medium : 0.0 (bad color) → 0.5 (changed but not #50C878) → 1.0 (exact match)
          Hard   : 0.2/tag correct (×3) + 0.4 correct order = max 1.0
        """
        if self.task_difficulty == "easy":
            node = self._find_node(self.dom, "hero-img")
            if not node:
                return 0.0
            alt = node.get("alt", "").lower().strip()
            if alt == "":
                return 0.0
            if len(alt) < 5 or alt in ("image", "img", "picture", "photo"):
                return 0.5
            return 1.0

        elif self.task_difficulty == "medium":
            node = self._find_node(self.dom, "upgrade-btn")
            if not node:
                return 0.0
            color = str(node.get("css", {}).get("color", "")).upper().strip()
            if color == "#50C878":
                return 1.0
            if color not in ("#E0F2E9", ""):
                return 0.5
            return 0.0

        elif self.task_difficulty == "hard":
            node = self._find_node(self.dom, "header-chaotic")
            if not node:
                return 0.0
            score = 0.0
            main   = self._find_node(node, "main-title")
            sub    = self._find_node(node, "subtitle")
            subsub = self._find_node(node, "sub-subtitle")
            if main   and main.get("type", "").lower()   == "h1": score += 0.2
            if sub    and sub.get("type", "").lower()    == "h2": score += 0.2
            if subsub and subsub.get("type", "").lower() == "h3": score += 0.2
            ids = [c.get("id") for c in node.get("children", [])]
            if ids == ["main-title", "subtitle", "sub-subtitle"]:
                score += 0.4
            return round(min(1.0, score), 4)

        return 0.0