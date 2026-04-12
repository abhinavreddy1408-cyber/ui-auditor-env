import os

def _clamp(v):
    try:
        score = float(v)
        return max(0.05, min(0.95, round(score, 4)))
    except Exception:
        return 0.05

def find_node(node, target_id):
    if not isinstance(node, dict):
        return None
    if node.get("id") == target_id:
        return node
    for child in node.get("children", []):
        result = find_node(child, target_id)
        if result:
            return result
    return None

def alt_text_grader(env) -> float:
    """Grade: did the agent add a descriptive alt attribute to the image?"""
    try:
        dom = env.dom if isinstance(env.dom, dict) else {}
        node = find_node(dom, "img_001") or find_node(dom, "hero-img")
        if node:
            # Check both node root and attributes dict
            attrs = node.get("attributes", {})
            alt = str(node.get("alt", attrs.get("alt", ""))).strip()
            if alt:
                if len(alt) > 10: # Descriptive
                    return _clamp(0.95)
                return _clamp(0.5) # Too generic
        return _clamp(0.05)
    except Exception:
        return 0.05

def contrast_grader(env) -> float:
    """Grade: did the agent fix the contrast using the brand palette (#50C878)?"""
    try:
        dom = env.dom if isinstance(env.dom, dict) else {}
        node = find_node(dom, "btn_001") or find_node(dom, "bad-contrast-div") or find_node(dom, "upgrade-btn")
        if node:
            styles = node.get("css", node.get("style", {}))
            color = str(styles.get("color", "")).strip().lower()
            
            # Brand emerald green
            if color in ("#50c878", "emerald", "rgb(80, 200, 120)"):
                return _clamp(0.95)
            
            # Improved contrast but not brand color (any non-bad color)
            bad_colors = {"", "red", "#ff0000", "#f00", "#e1e1e1", "inherit"}
            if color and color not in bad_colors:
                return _clamp(0.7)
        return _clamp(0.05)
    except Exception:
        return 0.05

def hierarchy_grader(env) -> float:
    """Grade: are headings (H1, H2, H3) in correct semantic and visual order?"""
    try:
        headings = []
        def collect_headings(node):
            tag = str(node.get("type", node.get("tag", ""))).lower()
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                try:
                    headings.append({"level": int(tag[1]), "id": node.get("id")})
                except: pass
            for child in node.get("children", []):
                collect_headings(child)

        dom = env.dom if isinstance(env.dom, dict) else {}
        collect_headings(dom)

        if not headings:
            return _clamp(0.05)

        # check levels 1, 2, 3...
        levels = [h["level"] for h in headings]
        violations = 0
        
        # Rule 1: Must start with H1
        if levels[0] != 1:
            violations += 1
            
        # Rule 2: Sequential (no jumps like H1 -> H3)
        for i in range(1, len(levels)):
            if levels[i] > levels[i-1] + 1:
                violations += 1
        
        # Rule 3: Only one H1 (best practice)
        if levels.count(1) > 1:
            violations += 0.5

        score = max(0.1, 0.95 - (violations * 0.3))
        return _clamp(score)
    except Exception:
        return 0.05

def label_grader(env) -> float:
    """Grade: does the input have a label, aria-label, or aria-labelledby?"""
    try:
        dom = env.dom if isinstance(env.dom, dict) else {}
        node = find_node(dom, "input_001")
        if node:
            attrs = node.get("attributes", {})
            # Check for various labeling methods
            has_aria = node.get("aria-label") or attrs.get("aria-label") or \
                       node.get("aria-labelledby") or attrs.get("aria-labelledby")
            
            if has_aria:
                return _clamp(0.95)
            
            if node.get("label") or attrs.get("label"):
                return _clamp(0.85)

            if node.get("placeholder") or attrs.get("placeholder"):
                return _clamp(0.4) # Placeholder is not a label but better than nothing
        return _clamp(0.05)
    except Exception:
        return 0.05

def landmark_grader(env) -> float:
    """Grade: does the page use semantic landmark elements (nav, main, header, footer)?"""
    try:
        found_landmarks = set()
        landmarks = {"nav", "main", "header", "footer", "aside", "section"}
        
        def scan(node):
            tag = str(node.get("type", node.get("tag", ""))).lower()
            if tag in landmarks:
                found_landmarks.add(tag)
            for child in node.get("children", []):
                scan(child)
        
        dom = env.dom if isinstance(env.dom, dict) else {}
        scan(dom)
        
        # Score based on variety of landmarks
        count = len(found_landmarks)
        if count >= 3:
            return _clamp(0.95)
        if count >= 1:
            return _clamp(0.5 + (count * 0.1))
        return _clamp(0.05)
    except Exception:
        return 0.05
