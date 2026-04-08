import copy
from typing import Any, Dict, List, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import (
    Action as OpenEnvAction,
    EnvironmentMetadata,
    Observation as OpenEnvObservation,
    State,
)
from pydantic import BaseModel, Field


SCORE_EPS = 1e-3  # keep every reward strictly within (0, 1)


class Action(OpenEnvAction):
    action_type: str = Field(
        ...,
        description="One of: 'update_attribute', 'modify_css', 'reorder_nodes'",
    )
    node_id: str = Field(..., description="The ID of the DOM node to act upon")
    attr_name: Optional[str] = Field(
        None, description="Attribute name for update_attribute"
    )
    new_value: Optional[str] = Field(
        None, description="New value for update_attribute"
    )
    css_property: Optional[str] = Field(
        None, description="CSS property for modify_css"
    )
    new_hex_code: Optional[str] = Field(
        None, description="New hex code for modify_css"
    )
    new_child_order: Optional[List[str]] = Field(
        None, description="List of child IDs for reorder_nodes"
    )


class Observation(OpenEnvObservation):
    dom_state: Dict[str, Any] = Field(
        ..., description="Pure Python dictionary representing the DOM"
    )
    task_description: str = Field(
        ..., description="Instructions for the current task"
    )
    current_score: float = Field(
        0.0, description="Current dense reward score (strictly between 0 and 1)"
    )
    feedback: str = Field(..., description="Feedback from the environment")


class RewardModel(BaseModel):
    score: float = Field(..., description="Dense reward strictly between 0 and 1")
    is_terminal: bool = Field(
        ..., description="True if score ~= 1.0 or max steps reached"
    )


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
                    "content": "Discover Premium Dashboard Analytics",
                },
                {
                    "id": "hero-img",
                    "type": "img",
                    "src": "/assets/hero-dribbble-mockup.png",
                    "alt": "",
                    "css": {
                        "border-radius": "12px",
                        "box-shadow": "0 4px 12px rgba(0,0,0,0.15)",
                        "border": "1px solid #FFD700",
                    },
                },
            ],
        }
    ],
}

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
                        "color": "#E0F2E9",
                        "border-radius": "8px",
                        "padding": "12px 24px",
                        "font-family": "Inter, sans-serif",
                        "font-weight": "600",
                    },
                }
            ],
        }
    ],
}

DOM_HARD = {
    "id": "root",
    "type": "div",
    "children": [
        {
            "id": "header-chaotic",
            "type": "div",
            "children": [
                {
                    "id": "sub-subtitle",
                    "type": "div",
                    "content": "Overview metrics & active users",
                },
                {
                    "id": "main-title",
                    "type": "h2",
                    "content": "Dashboard Homepage",
                    "css": {"color": "#50C878", "font-weight": "bold"},
                },
                {
                    "id": "subtitle",
                    "type": "h3",
                    "content": "User Growth Trends",
                },
            ],
        }
    ],
}


class UIAuditorEnv(Environment[Action, Observation, State]):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, task_difficulty: str = "easy"):
        self.task_difficulty = task_difficulty.lower()
        self.dom: Dict[str, Any] = {}
        self.task_desc = ""
        self.steps = 0
        self.max_steps = 15
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.reset(task_difficulty=self.task_difficulty)

    @staticmethod
    def _bounded_score(raw_score: float) -> float:
        """Clamp reward into the open interval (0, 1) expected by the evaluator."""
        return max(SCORE_EPS, min(1 - SCORE_EPS, raw_score))

    @property
    def _perfect_threshold(self) -> float:
        return 1 - SCORE_EPS

    def _select_task(self, task_name: Optional[str] = None) -> str:
        selected = (task_name or self.task_difficulty or "easy").lower()
        if selected not in {"easy", "medium", "hard"}:
            raise ValueError("Task must be 'easy', 'medium', or 'hard'")
        self.task_difficulty = selected
        return selected

    def _load_task(self, selected_task: str, episode_id: Optional[str] = None) -> None:
        self.steps = 0
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)

        if selected_task == "easy":
            self.dom = copy.deepcopy(DOM_EASY)
            self.task_desc = (
                "Accessibility Fix: Find the hero image (id: 'hero-img') missing "
                "its 'alt' text and add a descriptive one about a premium dashboard."
            )
        elif selected_task == "medium":
            self.dom = copy.deepcopy(DOM_MEDIUM)
            self.task_desc = (
                "WCAG Compliance Fix: Fix the CTA button (id: 'upgrade-btn') color "
                "contrast. Change its CSS 'color' to emerald green ('#50C878') for "
                "adequate readability on white."
            )
        else:
            self.dom = copy.deepcopy(DOM_HARD)
            self.task_desc = (
                "Semantic Structuring: In the container (id: 'header-chaotic'), "
                "change tags of main-title to h1, subtitle to h2, and "
                "sub-subtitle to h3. Then reorder their IDs logically "
                "[main-title, subtitle, sub-subtitle]."
            )

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_difficulty: Optional[str] = None,
        task_id: Optional[str] = None,
        task: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        del seed, kwargs
        selected_task = self._select_task(task_difficulty or task_id or task)
        self._load_task(selected_task, episode_id=episode_id)
        return self._build_observation()

    def _build_observation(self) -> Observation:
        score = self._calculate_reward()
        done = score >= self._perfect_threshold or self.steps >= self.max_steps

        if score >= self._perfect_threshold:
            feedback = "Task completed perfectly! (Score ~1.0)"
        elif self.steps >= self.max_steps:
            feedback = "Max steps reached without fully resolving the issue."
        else:
            feedback = (
                f"Currently at {score * 100}%. Keep improving the UI structure."
            )

        return Observation(
            dom_state=self.dom,
            task_description=self.task_desc,
            current_score=score,
            feedback=feedback,
            reward=score,
            done=done,
            metadata={
                "task_difficulty": self.task_difficulty,
                "step_count": self.steps,
            },
        )

    def _find_node(self, node: Dict[str, Any], target_id: str) -> Optional[Dict[str, Any]]:
        if node.get("id") == target_id:
            return node
        for child in node.get("children", []):
            found = self._find_node(child, target_id)
            if found:
                return found
        return None

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        task_difficulty: Optional[str] = None,
        task_id: Optional[str] = None,
        task: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        del timeout_s, kwargs

        requested_task = (
            task_difficulty
            or task_id
            or task
            or action.metadata.get("task_difficulty")
            or action.metadata.get("task_id")
            or action.metadata.get("task")
        )
        if requested_task:
            previous_task = self.task_difficulty
            selected_task = self._select_task(requested_task)
            if selected_task != previous_task or not self.dom:
                self._load_task(selected_task, episode_id=self._state.episode_id)

        self.steps += 1
        self._state.step_count = self.steps
        node = self._find_node(self.dom, action.node_id)

        if not node:
            obs = self._build_observation()
            obs.feedback = f"Evaluation failed: Node with ID '{action.node_id}' not found."
            obs.metadata["last_action"] = action.model_dump()
            return obs

        if action.action_type == "update_attribute":
            if action.attr_name and action.new_value is not None:
                if action.attr_name not in {"content", "id"}:
                    node[action.attr_name] = action.new_value
        elif action.action_type == "modify_css":
            if action.css_property and action.new_hex_code is not None:
                if "css" not in node:
                    node["css"] = {}
                node["css"][action.css_property] = action.new_hex_code
        elif action.action_type == "reorder_nodes":
            if action.new_child_order and "children" in node:
                current_children = {child["id"]: child for child in node["children"]}
                new_children = []
                for child_id in action.new_child_order:
                    if child_id in current_children:
                        new_children.append(current_children[child_id])
                for child in node["children"]:
                    if child["id"] not in action.new_child_order:
                        new_children.append(child)
                node["children"] = new_children

        obs = self._build_observation()
        obs.metadata["last_action"] = action.model_dump()
        return obs

    def _calculate_reward(self) -> float:
        if self.task_difficulty == "easy":
            node = self._find_node(self.dom, "hero-img")
            if not node:
                return self._bounded_score(0.0)

            alt = node.get("alt", "").lower().strip()
            if alt == "":
                return self._bounded_score(0.0)
            if len(alt) < 5 or alt in {"image", "img", "picture"}:
                return self._bounded_score(0.5)
            return self._bounded_score(1.0)

        if self.task_difficulty == "medium":
            node = self._find_node(self.dom, "upgrade-btn")
            if not node:
                return self._bounded_score(0.0)

            css = node.get("css", {})
            color = str(css.get("color", "")).upper().strip()
            if color == "#50C878":
                return self._bounded_score(1.0)
            if color not in {"#E0F2E9", ""}:
                return self._bounded_score(0.5)
            return self._bounded_score(0.0)

        if self.task_difficulty == "hard":
            node = self._find_node(self.dom, "header-chaotic")
            if not node:
                return self._bounded_score(0.0)

            score = 0.0
            main = self._find_node(node, "main-title")
            sub = self._find_node(node, "subtitle")
            subsub = self._find_node(node, "sub-subtitle")

            if main and main.get("type", "").lower() == "h1":
                score += 0.2
            if sub and sub.get("type", "").lower() == "h2":
                score += 0.2
            if subsub and subsub.get("type", "").lower() == "h3":
                score += 0.2

            children_ids = [child.get("id") for child in node.get("children", [])]
            if children_ids == ["main-title", "subtitle", "sub-subtitle"]:
                score += 0.4

            return self._bounded_score(round(min(1.0, score), 2))

        return self._bounded_score(0.0)

    @property
    def state(self) -> State:
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="ui-accessibility-auditor",
            description="Automated Web UI and accessibility auditor environment.",
            version="0.1.0",
            author="V.Abhinav",
        )
