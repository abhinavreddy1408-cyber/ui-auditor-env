# Architecture: Automated Web UI & Accessibility Auditor
## 3-Layer Architecture
### 1. Directive Layer -> what to do
The Directive Layer is responsible for defining the overarching goal for the AI agent at each task level (Easy, Medium, Hard). It sets the context of the simulated Dribbble-inspired UI (emerald green #50C878 and soft gold #FFD700).

**Goal Definition**: Present the current state of the DOM and the specific accessibility or UI issue that needs to be resolved.
**Constraints**: Identify the boundaries of the task (e.g., "Do not alter the user-facing text content while fixing the structure").

### 2. Orchestration Layer -> Decision
The Orchestration Layer bridges the high-level directives with actionable execution steps. The agent must reason about the DOM state (Observation) and decide which actions to take.

**Planning Box**: "For UI models -> Dribbble"
**State Analysis**: Parse the pure Python dictionary representing the DOM.
**Strategy Formulation**:
Evaluate current attributes versus desired accessibility standards (WCAG guidelines).
Plan a sequence of actions (e.g., identify node -> modify CSS -> verify contrast).

### 3. Execution Layer -> Execution
The Execution Layer translates the Orchestration Layer's decisions into concrete, perfectly structured Action inputs using Pydantic models.

**Action Construction**: Build the precise JSON/Pydantic payloads required by the environment's action space.
**Environment Interaction**: Submit actions like update_attribute, modify_css, or reorder_nodes.
**Feedback Processing**: Receive the Observation and the dense Reward (0.0 to 1.0) to adjust future execution if the score hasn't reached 1.0.

## Environment Specification
### Observation Space
A strictly typed Pydantic model returning the pure Python dictionary representation of the DOM, the current task description, and the recent score.
### Action Space
A strictly typed Pydantic model allowing the agent to mutate the DOM:

update_attribute(node_id: str, attr_name: str, new_value: str)
modify_css(node_id: str, css_property: str, new_hex_code: str)
reorder_nodes(parent_id: str, new_child_order: list[str])

### State & Reset

reset(): Initializes the DOM to the flawed state for the selected task (Easy, Medium, Hard).
state(): Returns the current DOM dictionary and task progress.
step(action): Applies the mutation, calculates the dense reward, and transitions the state.

## Task Curriculum & Reward Logic (Dense Reward 0.0 - 1.0)
**1. Easy Task: Hero Image Accessibility**

**Objective**: Find a hero image missing alt text and add a descriptive one.
**Failure State**: {"type": "img", "id": "hero-img", "src": "/assets/hero.png", "alt": ""}
**Reward Shaping**:
0.0: No change.
0.5: alt attribute added but is generic (e.g., "image").
1.0: alt attribute added with descriptive text (e.g., "Premium dashboard preview").
**2. Medium Task: CTA Button Color Contrast (WCAG)**
**Objective**: Fix a CTA button with poor color contrast (fails WCAG) by updating CSS to use the palette (#50C878 or #FFD700 appropriately).
**Failure State**: Light green text on a white background.
**Reward Shaping**:
0.0: No change or worse contrast.
0.5: Contrast improved but still fails WCAG AA standard.
1.0: Proper color contrast achieved using correct brand palette (#50C878 / #FFD700).
**3. Hard Task: Semantic Header Restructuring**
**Objective**: Reorder a chaotic header DOM into clean semantic structure (H1 -> H2 -> H3, proper <nav>) without losing content.
**Failure State**: H3 before H1, nested improperly inside divs instead of <header>.
**Reward Shaping**:
0.0: No change.
0.3: Some nodes reordered, but hierarchical errors remain.
0.7: Correct tag changes (H1, H2, nav) but incorrect visual order.
1.0: Perfect structural order and semantic tags without any content loss.
