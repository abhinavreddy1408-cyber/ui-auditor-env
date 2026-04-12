import traceback
from env import Action, UIAuditorEnv
import graders

def test_easy():
    print("Testing Easy Task (Alt Text)...")
    env = UIAuditorEnv(task_difficulty="easy")
    env.reset(grader=graders.alt_text_grader)
    action = Action(
        action_type="update_attribute",
        node_id="hero-img",
        attribute="alt",
        value="A beautiful dashboard for premium analytical insights",
    )
    env.step(action)
    obs = env.state()
    print("Easy Score:", obs.current_score)
    assert obs.current_score >= 0.94

def test_medium():
    print("Testing Medium Task (Contrast)...")
    env = UIAuditorEnv(task_difficulty="medium")
    env.reset(grader=graders.contrast_grader)
    action = Action(
        action_type="modify_css",
        node_id="btn_001",
        property="color",
        value="#50C878",
    )
    env.step(action)
    obs = env.state()
    print("Medium Score:", obs.current_score)
    assert obs.current_score >= 0.94

def test_hard():
    print("Testing Hard Task (Hierarchy)...")
    env = UIAuditorEnv(task_difficulty="hard")
    env.reset(grader=graders.hierarchy_grader)

    # Reorder nodes to fix hierarchy: h1, then h2, then h3
    action = Action(
        action_type="reorder_nodes",
        node_id="root",
        new_child_order=["h1_001", "h2_001", "h3_001", "input_001"],
    )
    env.step(action)
    obs = env.state()
    print("Hard Score:", obs.current_score)
    assert obs.current_score >= 0.94

def test_extra():
    print("Testing Extra Task (Labels)...")
    env = UIAuditorEnv(task_difficulty="hard")
    env.reset(grader=graders.label_grader)
    action = Action(
        action_type="update_attribute",
        node_id="input_001",
        attribute="aria-label",
        value="Username input field",
    )
    env.step(action)
    obs = env.state()
    print("Extra Score:", obs.current_score)
    assert obs.current_score >= 0.94

if __name__ == "__main__":
    try:
        test_easy()
        test_medium()
        test_hard()
        test_extra()
        print("\n✅ All tests passed!")
    except Exception:
        traceback.print_exc()
