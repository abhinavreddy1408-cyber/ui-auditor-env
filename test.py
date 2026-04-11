import traceback

from env import Action, UIAuditorEnv


def test_easy():
    print("Testing Easy Task...")
    env = UIAuditorEnv(task_difficulty="easy")
    env.reset()
    action = Action(
        action_type="update_attribute",
        node_id="hero-img",
        attr_name="alt",
        new_value="A beautiful dashboard for premium analytical insights",
    )
    obs, reward, done, info = env.step(action)
    print("Easy Score:", obs.current_score)
<<<<<<< Updated upstream
    assert obs.current_score >= 0.94
=======
    assert obs.current_score >= 0.999
>>>>>>> Stashed changes


def test_medium():
    print("Testing Medium Task...")
    env = UIAuditorEnv(task_difficulty="medium")
    env.reset()
    action = Action(
        action_type="modify_css",
        node_id="upgrade-btn",
        css_property="color",
        new_hex_code="#50C878",
    )
    obs, reward, done, info = env.step(action)
    print("Medium Score:", obs.current_score)
<<<<<<< Updated upstream
    assert obs.current_score >= 0.94
=======
    assert obs.current_score >= 0.999
>>>>>>> Stashed changes


def test_hard():
    print("Testing Hard Task...")
    env = UIAuditorEnv(task_difficulty="hard")
    env.reset()

    actions = [
        Action(
            action_type="update_attribute",
            node_id="main-title",
            attr_name="type",
            new_value="h1",
        ),
        Action(
            action_type="update_attribute",
            node_id="subtitle",
            attr_name="type",
            new_value="h2",
        ),
        Action(
            action_type="update_attribute",
            node_id="sub-subtitle",
            attr_name="type",
            new_value="h3",
        ),
        Action(
            action_type="reorder_nodes",
            node_id="header-chaotic",
            new_child_order=["main-title", "subtitle", "sub-subtitle"],
        ),
    ]

    obs = None
    for action in actions:
        obs, reward, done, info = env.step(action)

    assert obs is not None
    print("Hard Score:", obs.current_score)
<<<<<<< Updated upstream
    assert obs.current_score >= 0.94
=======
    assert obs.current_score >= 0.999
>>>>>>> Stashed changes


if __name__ == "__main__":
    try:
        test_easy()
        test_medium()
        test_hard()
        print("All tests passed perfectly!")
    except Exception:
        traceback.print_exc()
