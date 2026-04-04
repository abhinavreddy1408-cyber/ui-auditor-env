from env import UIAuditorEnv, Action
import traceback

def test_easy():
    print("Testing Easy Task...")
    env = UIAuditorEnv(task_difficulty="easy")
    obs = env.state()
    # Correct action
    action = Action(action_type="update_attribute", node_id="hero-img", attr_name="alt", new_value="A beautiful dashboard for premium analytical insights")
    obs, reward = env.step(action)
    print("Easy Score:", reward.score)
    assert reward.score == 1.0


def test_medium():
    print("Testing Medium Task...")
    env = UIAuditorEnv(task_difficulty="medium")
    obs = env.state()
    # Correct action
    action = Action(action_type="modify_css", node_id="upgrade-btn", css_property="color", new_hex_code="#50C878")
    obs, reward = env.step(action)
    print("Medium Score:", reward.score)
    assert reward.score == 1.0


def test_hard():
    print("Testing Hard Task...")
    env = UIAuditorEnv(task_difficulty="hard")
    obs = env.state()
    
    a1 = Action(action_type="update_attribute", node_id="main-title", attr_name="type", new_value="h1")
    a2 = Action(action_type="update_attribute", node_id="subtitle", attr_name="type", new_value="h2")
    a3 = Action(action_type="update_attribute", node_id="sub-subtitle", attr_name="type", new_value="h3")
    a4 = Action(action_type="reorder_nodes", node_id="header-chaotic", new_child_order=["main-title", "subtitle", "sub-subtitle"])
    
    env.step(a1)
    env.step(a2)
    env.step(a3)
    obs, reward = env.step(a4)
    print("Hard Score:", reward.score)
    assert reward.score == 1.0


if __name__ == "__main__":
    try:
        test_easy()
        test_medium()
        test_hard()
        print("All tests passed perfectly!")
    except Exception as e:
        traceback.print_exc()
