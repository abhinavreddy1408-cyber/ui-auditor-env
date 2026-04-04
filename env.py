from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import copy

# ============================================================================
# Step 2: Planning & Environment Design
# OpenEnv Spec 100%: Strictly typed Pydantic models & pure dictionary DOM
# ============================================================================

# --- 1. Pydantic Models for OpenEnv Spec ---

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
    current_score: float = Field(0.0, description="Current dense reward score (0.0 to 1.0)")
    is_done: bool = Field(False, description="Whether the task is successfully completed")
    feedback: str = Field(..., description="Feedback from the last action or current status")

class RewardModel(BaseModel):
    score: float = Field(..., description="Dense reward between 0.0 and 1.0")
    is_terminal: bool = Field(..., description="True if score == 1.0 or max steps reached")

# --- 2. Defining the DOM Scenarios (Dribbble-Inspired UI) ---

# Easy Task: Hero block with missing alt text.
DOM_EASY = {
    "id": "root",
    "type": "div",
    "children": [
        {
            "id": "hero-section",
            "type": "section",
            "children": [
                {
                    "id": "hero-text",
                    "type": "h1",
                    "content": "Discover Premium Dashboard Analytics"
                },
                {
                    "id": "hero-img",
                    "type": "img",
                    "src": "/assets/hero-dribbble-mockup.png",
                    "alt": "",  # Issue: Missing Alt Text
                    "css": {
                        "border-radius": "12px", 
                        "box-shadow": "0 4px 12px rgba(0,0,0,0.15)",
                        "border": "1px solid #FFD700"  # Soft gold accent
                    }
                }
            ]
        }
    ]
}

# Medium Task: CTA Button with bad contrast (light green text on white).
DOM_MEDIUM = {
    "id": "root",
    "type": "div",
    "children": [
        {
            "id": "cta-container",
            "type": "div",
            "css": {"padding": "40px", "background-color": "#FFFFFF"},
            "children": [
                {
                    "id": "upgrade-btn",
                    "type": "button",
                    "content": "Upgrade to Pro",
                    "css": {
                        "background-color": "#FFFFFF",
                        "color": "#E0F2E9", # Issue: Fails WCAG Contrast
                        "border-radius": "8px",
                        "padding": "12px 24px",
                        "font-family": "Inter, sans-serif",
                        "font-weight": "600"
                    }
                }
            ]
        }
    ]
}

# Hard Task: Structurally chaotic header requiring semantic tags and reordering.
DOM_HARD = {
    "id": "root",
    "type": "div",
    "children": [
        {
            "id": "header-chaotic",
            "type": "div", # Should ideally be changed to <nav> or <header>
            "children": [
                {
                    "id": "sub-subtitle", # Misplaced at the top
                    "type": "div", # Issue: Should be h3
                    "content": "Overview metrics & active users"
                },
                {
                    "id": "main-title",
                    "type": "h2", # Issue: Should be h1
                    "content": "Dashboard Homepage",
                    "css": {"color": "#50C878", "font-weight": "bold"} # Emerald Green
                },
                {
                    "id": "subtitle",
                    "type": "h3", # Issue: Should be h2
                    "content": "User Growth Trends"
                }
            ]
        }
    ]
}

# --- 3. Environment Engine ---

class UIAuditorEnv:
    def __init__(self, task_difficulty: str = "easy"):
        self.task_difficulty = task_difficulty.lower()
        self.dom = {}
        self.steps = 0
        self.max_steps = 15
        self.reset()
        
    def reset(self) -> Observation:
        self.steps = 0
        if self.task_difficulty == "easy":
            self.dom = copy.deepcopy(DOM_EASY)
            self.task_desc = "Accessibility Fix: Find the hero image (id: 'hero-img') missing its 'alt' text and add a descriptive one about a premium dashboard."
        elif self.task_difficulty == "medium":
            self.dom = copy.deepcopy(DOM_MEDIUM)
            self.task_desc = "WCAG Compliance Fix: Fix the CTA button (id: 'upgrade-btn') color contrast. Change its CSS 'color' to emerald green ('#50C878') for adequate readability on white."
        elif self.task_difficulty == "hard":
            self.dom = copy.deepcopy(DOM_HARD)
            self.task_desc = "Semantic Structuring: In the container (id: 'header-chaotic'), change tags of main-title to h1, subtitle to h2, and sub-subtitle to h3. Then reorder their IDs logically [main-title, subtitle, sub-subtitle]."
        else:
            raise ValueError("Task must be 'easy', 'medium', or 'hard'")
            
        return self.state()

    def state(self) -> Observation:
        score = self._calculate_reward()
        is_done = score >= 1.0 or self.steps >= self.max_steps
        
        feedback = "Task completed perfectly! (Score 1.0)" if score >= 1.0 else f"Currently at {score * 100}%. Keep improving the UI structure."
        if self.steps >= self.max_steps and score < 1.0:
            feedback = "Max steps reached without fully resolving the issue."
            
        return Observation(
            dom_state=self.dom,
            task_description=self.task_desc,
            current_score=score,
            is_done=is_done,
            feedback=feedback
        )

    def _find_node(self, node: dict, target_id: str) -> Optional[dict]:
        if node.get("id") == target_id:
            return node
        for child in node.get("children", []):
            found = self._find_node(child, target_id)
            if found: return found
        return None

    def step(self, action: Action) -> tuple[Observation, RewardModel]:
        self.steps += 1
        node = self._find_node(self.dom, action.node_id)
        
        if not node:
            obs = self.state()
            obs.feedback = f"Evaluation failed: Node with ID '{action.node_id}' not found."
            return obs, RewardModel(score=obs.current_score, is_terminal=obs.is_done)

        # Process standard actions
        if action.action_type == "update_attribute":
            if action.attr_name and action.new_value is not None:
                if action.attr_name in ["content", "id"]:
                    pass  # Prevent cheating by altering IDs or content
                else:
                    node[action.attr_name] = action.new_value
                    
        elif action.action_type == "modify_css":
            if action.css_property and action.new_hex_code is not None:
                if "css" not in node:
                    node["css"] = {}
                node["css"][action.css_property] = action.new_hex_code
                
        elif action.action_type == "reorder_nodes":
            if action.new_child_order and "children" in node:
                # Reconstruct children in the requested order if IDs match
                current_children = {c["id"]: c for c in node["children"]}
                new_children = []
                # Keep matching ones in order
                for cid in action.new_child_order:
                    if cid in current_children:
                        new_children.append(current_children[cid])
                
                # Make sure we didn't lose nodes (append remaining at the end)
                for c in node["children"]:
                    if c["id"] not in action.new_child_order:
                        new_children.append(c)
                
                node["children"] = new_children

        obs = self.state()
        reward = RewardModel(score=obs.current_score, is_terminal=obs.is_done)
        return obs, reward

    def _calculate_reward(self) -> float:
        """Dense Reward Shaping Logic"""
        if self.task_difficulty == "easy":
            node = self._find_node(self.dom, "hero-img")
            if not node: return 0.0
            
            alt = node.get("alt", "").lower().strip()
            if alt == "": return 0.0
            if len(alt) < 5 or alt in ["image", "img", "picture"]: return 0.5
            return 1.0  # Proper description added

        elif self.task_difficulty == "medium":
            node = self._find_node(self.dom, "upgrade-btn")
            if not node: return 0.0
            
            css = node.get("css", {})
            color = str(css.get("color", "")).upper().strip()
            
            if color == "#50C878": return 1.0  # Perfect WCAG Emerald fix
            if color != "#E0F2E9" and color != "": return 0.5  # Partial try, but not the exact brand palette
            return 0.0

        elif self.task_difficulty == "hard":
            node = self._find_node(self.dom, "header-chaotic")
            if not node: return 0.0
            score = 0.0
            
            # 1. Check semantics tag updates (+0.6 max)
            main = self._find_node(node, "main-title")
            sub = self._find_node(node, "subtitle")
            subsub = self._find_node(node, "sub-subtitle")
            
            if main and main.get("type", "").lower() == "h1": score += 0.2
            if sub and sub.get("type", "").lower() == "h2": score += 0.2
            if subsub and subsub.get("type", "").lower() == "h3": score += 0.2
            
            # 2. Check reordering logic (+0.4)
            children_ids = [c.get("id") for c in node.get("children", [])]
            if children_ids == ["main-title", "subtitle", "sub-subtitle"]:
                score += 0.4
                
            return round(min(1.0, score), 2)
