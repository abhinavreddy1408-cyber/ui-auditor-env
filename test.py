import traceback

from env import Action, UIAuditorEnv


def test_easy():
    print("Testing Easy Task...")
    env = UIAuditorEnv(task_difficulty="easy")
    env.reset(task_difficulty="easy")
    action = Action(
        action_type="update_attribute",
        node_id="hero-img",
        attr_name="alt",
        new_value="A beautiful dashboard for premium analytical insights",
    )
    obs = env.step(action)
    print("Easy Score:", obs.current_score)
    assert obs.current_score == 1.0


def test_medium():
    print("Testing Medium Task...")
    env = UIAuditorEnv(task_difficulty="medium")
    env.reset(task_difficulty="medium")
    action = Action(
        action_type="modify_css",
        node_id="upgrade-btn",
        css_property="color",
        new_hex_code="#50C878",
    )
    obs = env.step(action)
    print("Medium Score:", obs.current_score)
    assert obs.current_score == 1.0


def test_hard():
    print("Testing Hard Task...")
    env = UIAuditorEnv(task_difficulty="hard")
    env.reset(task_difficulty="hard")

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
        obs = env.step(action)

    assert obs is not None
    print("Hard Score:", obs.current_score)
    assert obs.current_score == 1.0


if __name__ == "__main__":
    try:
        test_easy()
        test_medium()
        test_hard()
        print("All tests passed perfectly!")
    except Exception:
        traceback.print_exc()
