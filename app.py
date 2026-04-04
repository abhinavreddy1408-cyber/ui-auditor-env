import gradio as gr
import json
from env import UIAuditorEnv, Action

# ============================================================
# Automated Web UI & Accessibility Auditor — Interactive Demo
# Scalar × Meta & Hugging Face Agentic AI Hackathon
# ============================================================

def run_demo(task_difficulty: str, action_type: str, node_id: str,
             attr_name: str, new_value: str,
             css_property: str, new_hex_code: str,
             new_child_order: str):
    env = UIAuditorEnv(task_difficulty=task_difficulty.lower())
    obs = env.reset()

    initial_dom = json.dumps(obs.dom_state, indent=2)
    initial_score = obs.current_score
    task_desc = obs.task_description

    # Build Action
    try:
        child_order = [x.strip() for x in new_child_order.split(",")] if new_child_order.strip() else None
        action = Action(
            action_type=action_type,
            node_id=node_id,
            attr_name=attr_name if attr_name.strip() else None,
            new_value=new_value if new_value.strip() else None,
            css_property=css_property if css_property.strip() else None,
            new_hex_code=new_hex_code if new_hex_code.strip() else None,
            new_child_order=child_order,
        )
        obs, reward = env.step(action)
        result_dom = json.dumps(obs.dom_state, indent=2)
        result_score = reward.score
        result_feedback = obs.feedback
        status = "✅ Action Applied Successfully!" if reward.score >= 1.0 else "⚠️ Action Applied — Not Perfect Yet"
    except Exception as e:
        result_dom = initial_dom
        result_score = initial_score
        result_feedback = f"❌ Error: {str(e)}"
        status = "❌ Action Failed"

    score_bar = f"{'█' * int(result_score * 20)}{'░' * (20 - int(result_score * 20))} {result_score:.2f}/1.0"

    return (
        f"📋 Task: {task_desc}",
        initial_dom,
        status,
        result_dom,
        f"Dense Reward: {score_bar}",
        result_feedback,
    )


def get_task_hint(task):
    hints = {
        "Easy": {
            "action_type": "update_attribute",
            "node_id": "hero-img",
            "attr_name": "alt",
            "new_value": "A premium analytics dashboard for modern data teams",
            "css_property": "",
            "new_hex_code": "",
            "new_child_order": "",
        },
        "Medium": {
            "action_type": "modify_css",
            "node_id": "upgrade-btn",
            "attr_name": "",
            "new_value": "",
            "css_property": "color",
            "new_hex_code": "#50C878",
            "new_child_order": "",
        },
        "Hard": {
            "action_type": "reorder_nodes",
            "node_id": "header-chaotic",
            "attr_name": "",
            "new_value": "",
            "css_property": "",
            "new_hex_code": "",
            "new_child_order": "main-title, subtitle, sub-subtitle",
        },
    }
    h = hints.get(task, hints["Easy"])
    return (h["action_type"], h["node_id"], h["attr_name"],
            h["new_value"], h["css_property"], h["new_hex_code"], h["new_child_order"])


# --- Gradio UI ---
with gr.Blocks(
    title="UI Auditor Env — OpenEnv Hackathon",
    theme=gr.themes.Base(
        primary_hue="emerald",
        secondary_hue="yellow",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css="""
    .header-box {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        border-radius: 12px; padding: 24px; margin-bottom: 16px;
        border: 1px solid #50C878;
    }
    .score-box { font-family: monospace; font-size: 1.1em; color: #50C878; }
    footer { display: none !important; }
    """
) as demo:

    gr.HTML("""
    <div class="header-box">
      <h1 style="color:#50C878;margin:0;font-size:1.8em;">🎨 Automated Web UI &amp; Accessibility Auditor</h1>
      <p style="color:#FFD700;margin:6px 0 0;font-size:1em;">
        Scalar × Meta &amp; Hugging Face Agentic AI Hackathon · OpenEnv Compatible
      </p>
      <p style="color:#aaa;margin:4px 0 0;font-size:0.85em;">
        A zero-browser, strictly-typed Pydantic DOM simulator with dense reward shaping (0.0 → 1.0)
      </p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Task Selection")
            task = gr.Radio(["Easy", "Medium", "Hard"], value="Easy", label="Task Difficulty")
            hint_btn = gr.Button("💡 Load Optimal Action", variant="secondary")

            gr.Markdown("### 🤖 Agent Action")
            action_type = gr.Dropdown(
                ["update_attribute", "modify_css", "reorder_nodes"],
                value="update_attribute", label="Action Type"
            )
            node_id = gr.Textbox(label="Node ID", value="hero-img")
            attr_name = gr.Textbox(label="attr_name (for update_attribute)", value="alt")
            new_value = gr.Textbox(label="new_value (for update_attribute)", value="")
            css_property = gr.Textbox(label="css_property (for modify_css)", value="")
            new_hex_code = gr.Textbox(label="new_hex_code (for modify_css)", value="")
            new_child_order = gr.Textbox(label="new_child_order (csv, for reorder_nodes)", value="")
            run_btn = gr.Button("🚀 Execute Action", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### 📊 Environment Output")
            task_display = gr.Textbox(label="Current Task", interactive=False)
            with gr.Row():
                dom_before = gr.Code(label="DOM Before (Initial State)", language="json", lines=12)
                dom_after = gr.Code(label="DOM After (Post Action)", language="json", lines=12)
            action_status = gr.Textbox(label="Action Status", interactive=False)
            score_display = gr.Textbox(label="Dense Reward Score", interactive=False, elem_classes=["score-box"])
            feedback_display = gr.Textbox(label="Environment Feedback", interactive=False)

    gr.Markdown("""
    ---
    ### 📋 Task Curriculum
    | Level | Objective | Target Score |
    |-------|-----------|-------------|
    | 🟢 **Easy** | Add descriptive `alt` text to hero image (`hero-img`) | 1.0 |
    | 🟡 **Medium** | Fix CTA button color contrast → Emerald `#50C878` WCAG fix | 1.0 |
    | 🔴 **Hard** | Semantic tag fix (h1/h2/h3) + reorder DOM nodes in `header-chaotic` | 1.0 |
    
    > **Dense Rewards**: Unlike binary pass/fail, scores range `0.0 → 1.0` giving agents partial credit for approximate fixes.
    """)

    # Event handlers
    run_btn.click(
        fn=run_demo,
        inputs=[task, action_type, node_id, attr_name, new_value, css_property, new_hex_code, new_child_order],
        outputs=[task_display, dom_before, action_status, dom_after, score_display, feedback_display]
    )

    def load_hint(t):
        return get_task_hint(t)

    hint_btn.click(
        fn=load_hint,
        inputs=[task],
        outputs=[action_type, node_id, attr_name, new_value, css_property, new_hex_code, new_child_order]
    )

    # Auto-load on start
    demo.load(
        fn=run_demo,
        inputs=[task, action_type, node_id, attr_name, new_value, css_property, new_hex_code, new_child_order],
        outputs=[task_display, dom_before, action_status, dom_after, score_display, feedback_display]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
