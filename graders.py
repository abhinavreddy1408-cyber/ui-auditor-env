import os

def _clamp(v):
    try:
        return max(0.05, min(0.95, float(v)))
    except Exception:
        return 0.05

def find_node(node, target_id):
    if node.get("id") == target_id:
        return node
    for child in node.get("children", []):
        result = find_node(child, target_id)
        if result:
            return result
    return None

def alt_text_grader(env) -> float:
    """Grade: did the agent add a non-empty alt attribute to img_001?"""
    try:
        dom = env.dom if isinstance(env.dom, dict) else {}
        # Support both img_001 (standard) and hero-img (EASY scenario)
        node = find_node(dom, "img_001") or find_node(dom, "hero-img")
        if node:
            alt = node.get("alt", "").strip()
            if alt and len(alt) > 3:
                return _clamp(0.95)
        return _clamp(0.05)
    except Exception:
        return 0.05

def contrast_grader(env) -> float:
    """Grade: did the agent fix the contrast for btn_001?"""
    try:
        dom = env.dom if isinstance(env.dom, dict) else {}
        node = find_node(dom, "btn_001") or find_node(dom, "bad-contrast-div")
        if node:
            # Check both 'style' and 'css' dictionaries (supporting different env versions)
            styles = node.get("style", {}) or node.get("css", {})
            color = styles.get("color", "").strip().lower()
            
            # emerald green (#50C878) is the target from README
            if color in ("#50c878", "emerald", "rgb(80, 200, 120)"):
                return _clamp(0.95)
            
            # fallback: any color that isn't the original 'bad' colors
            bad = {"", "red", "#ff0000", "#f00", "#e1e1e1", "inherit"}
            if color and color not in bad:
                return _clamp(0.8)
        return _clamp(0.05)
    except Exception:
        return 0.05

def hierarchy_grader(env) -> float:
    """Grade: are heading tags in correct sequential order (H1 > H2 > H3)?"""
    try:
        headings = []

        def collect_headings(node):
            tag = node.get("type", node.get("tag", "")).lower()
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                headings.append(int(tag[1]))
            for child in node.get("children", []):
                collect_headings(child)

        dom = env.dom if isinstance(env.dom, dict) else {}
        collect_headings(dom)

        if not headings:
            return 0.05

        violations = 0
        for i in range(1, len(headings)):
            # Violation if a heading level skips a level (e.g. H1 followed by H3)
            if headings[i] > headings[i - 1] + 1:
                violations += 1
            # Violation if H1 appears after another H1 (ideally only one H1)
            elif headings[i] == 1 and headings[i-1] == 1:
                violations += 0.5

        if violations == 0 and headings[0] == 1:
            return _clamp(0.95)
        return _clamp(max(0.1, 0.9 - violations * 0.2))
    except Exception:
        return 0.05

def label_grader(env) -> float:
    """Grade: does the input_001 have a valid label or aria-label?"""
    try:
        dom = env.dom if isinstance(env.dom, dict) else {}
        node = find_node(dom, "input_001")
        if node:
            # Check for aria-label or aria-labelledby
            attrs = node.get("attributes", {}) or node
            if attrs.get("aria-label") or attrs.get("aria-labelledby"):
                return _clamp(0.95)
            
            # Check label attribute (simplified mapping)
            if attrs.get("label"):
                return _clamp(0.9)
                
            # Check for placeholder as a weak fallback
            if attrs.get("placeholder"):
                return _clamp(0.4)
        return _clamp(0.05)
    except Exception:
        return 0.05
