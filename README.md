---
title: Ui Auditor Env
emoji: 🚀
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
---
# 🎨 Automated Web UI & Accessibility Auditor
<image-card alt="License" src="https://img.shields.io/badge/license-MIT-green" ></image-card>
<image-card alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue" ></image-card>
<image-card alt="OpenEnv" src="https://img.shields.io/badge/OpenEnv-Compatible-purple" ></image-card>

A premium, Dribbble-inspired simulated environment built specifically for the **Scalar × Meta & Hugging Face Agentic AI Hackathon**.

![AI Auditor Hero](file:///C:/Users/abhin/.gemini/antigravity/brain/bda56180-769c-4be9-ab9a-415a7d291efa/ai_auditor_hero_v2_1775312085429.png)

## 🌟 The Vision & Problem
Currently, generic AI web-agents are bloated—relying on memory-heavy headless Chromium models that scrape raw HTML blindly. For enterprise-grade accessibility (WCAG) and Semantic SEO auditing, this approach is imprecise, prone to hallucination, and extremely expensive to scale.

Our solution is the **Automated Web UI & Accessibility Auditor**—a zero-browser, strictly-typed Pydantic simulator built efficiently upon the **OpenEnv** framework. We transform the "black box" of web-agent interaction into a deterministic, surgical repair system that handles complex DOM mutations with 100% schema compliance.

## 🌟 Hackathon Highlights

**Pure Python OpenEnv Simulator**: Eliminates memory-heavy Chromium processes for blazing-fast inference inside 2 vCPU / 8 GB RAM limits.
**Strictly Typed Pydantic Interfaces**: Leverages the novel OpenAI v1.40.0+ strictly typed parser outputs to eliminate hallucinated actions.
**Dense Continuous Rewards**: Moving away from binary Pass/Fail, agents receive 0.0 to 1.0 scores relative to the exact semantic and visual quality of their fixes.

## 🏗️ Technical Architecture
### 1. Environment Description
The environment is structured in a **3-Layer Framework**:

**Directive**: Sets overarching goals (Easy, Medium, Hard) matching Dribbble aesthetics.
**Orchestration**: Extracts DOM trees into pure python dictionary representations and tracks UI nodes.
**Execution**: Validates Action schemas mapped to update_attribute, modify_css, or reorder_nodes.

### 2. Observation Space
A pure Pydantic model (Observation), yielding:

dom_state: The strict Python dictionary DOM.
task_description: Current objective for the AI agent.
current_score: The active dense reward (0.0->1.0).
feedback: Heuristics and string context of the simulation iteration.

### 3. Action Space
A strictly typed Pydantic Action enforcing valid agent mutations:

update_attribute(node_id, attr_name, new_value)
modify_css(node_id, css_property, new_hex_code)
reorder_nodes(node_id, new_child_order)

## 📋 Task Curriculum & Baseline Scores
Task | Objective | Agent Evaluation Focus | Target Baseline Score
--- | --- | --- | ---
🟢 **Easy** | **Hero Image Alt Text** | Appending contextual alt strings mapped precisely to the dashboard context. | 1.0
🟡 **Medium** | **Button Contrast (WCAG)** | Overwriting poor color CSS values with Emerald Green (#50C878). | 1.0
🔴 **Hard** | **Semantic Reorganization** | Converting chaotic div wrappers into H1 > H2 > H3, reordering nodes. | 1.0

## 🚀 Running the Environment Locally
**1. Install minimal dependencies:**
```bash
pip install -r requirements.txt
# OR using standard package build: pip install .
```
**2. Supply API Credentials (Compatible with generic backends like vLLM / OpenAI):**
```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export OPENAI_API_KEY="sk-your-actual-api-key"
```

**3. Run the Inference Baseline:**
```bash
python inference.py
```

## 📦 Containerization (Hugging Face Spaces Ready)
The environment strictly adheres to the requested bounds (8GB RAM / 2 vCPU):
```bash
docker build -t ui-auditor-env .
docker run --cpus="2.0" --memory="8g" -e OPENAI_API_KEY="your-key-here" ui-auditor-env
```
To run natively inside existing OpenEnv standard execution layers:
```bash
openenv run -f openenv.yaml
```

## 🤗 How to Deploy to Hugging Face Spaces
To officially submit your evaluator to Hugging Face Spaces:

**Create a Docker Space**: Navigate to huggingface.co/spaces and click **Create new Space**. Name it openenv-ui-auditor and select the **Docker** SDK (Blank).
**Push the Repository**: Simply upload or git push these exact project files directly into the Hugging Face Space repository.
**Configure API Secrets**: Navigate to the **Settings** tab of your Space, scroll to **Variables and secrets**, and add your runtime keys as secrets:

Name: OPENAI_API_KEY (or HF_TOKEN)
Value: sk-your-actual-api-key

**Build & Run**: The Space will automatically build the Dockerfile into a container optimized precisely for the default Hackathon hardware tier, rendering your OpenEnv evaluation suite perfectly online!
