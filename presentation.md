# Automated Web UI & Accessibility Auditor
### Scalar × Meta & Hugging Face Agentic AI Hackathon

## 🚀 The Vision
Currently, generic AI web-agents are bloated—relying on memory-heavy headless Chromium models that scrape raw HTML blindly. Our solution is the Automated Web UI & Accessibility Auditor—a zero-browser, strictly-typed Pydantic simulator built efficiently upon the OpenEnv framework.

Companies pay human auditors thousands of dollars to evaluate website accessibility (WCAG) and Semantic SEO structuring. We simulate exactly this enterprise necessity using an ultra-lightweight pure python dictionary AST (Abstract Syntax Tree).

## 💡 Technical Innovation
1.  **Zero-Browser Footprint:** We achieve full OpenEnv execution within the restrictive 2 vCPU / 8 GB RAM limits by completely abandoning Chromium web drivers. The DOM is manipulated purely in memory.
2.  **Strict Pydantic Grounding:** We eliminate AI hallucination natively. Leveraging the advanced `.parse()` parameters of `openai>=1.40.0`, agents cannot guess commands—they must strictly output `update_attribute`, `modify_css`, or `reorder_nodes`.
3.  **Dense Evaluator Shaping:** Archaic binary pass/fail mechanics are dead. Tasks like updating WCAG Contrast Ratios output detailed `0.0 -> 1.0` floats evaluating contextual metrics exactly mirroring real-world accessibility heuristics.

## 🏗️ 3-Layer Architecture
Our agent simulator environment is grounded logically by our custom 4-Step *Anti-Gravity Architecture Framework*:

-   **Directive Layer (What To Do):** Establishing the curriculum tasks (Easy: Alt Text Injection, Medium: WCAG Contrast Fixation, Hard: Semantic DOM Sequencing). Modeled structurally after premium **Dribbble Dashboards** (Emerald `#50C878` and Soft Gold `#FFD700`).
-   **Orchestration Layer (Decision Mechanics):** Processing agent interactions against the ideal AST, determining logical validity or content corruption penalties.
-   **Execution Layer (State Evolution):** Modifying the Pydantic DOM natively inside `step()` parameters yielding deterministic grading outputs.
