"""Checks a browser test can run on whatever the Lab page shows: text contrast,
a visible keyboard focus, no sideways scrolling, and touch targets.

Each check runs in the page and returns what failed, so a test asserts the list is
empty and the message names the element. WCAG 2.2 AA numbers: contrast 4.5:1 for
text (3:1 from 24 px, or 18.66 px bold), targets at least 24 by 24 CSS px.
"""

from typing import Any

# Text and form controls inside `root`, each compared with the colour behind it:
# every background up the tree is blended in, over the page's own background.
_CONTRAST_JS = """
([rootSelector, limit]) => {
  const root = document.querySelector(rootSelector);
  if (!root) return [{ problem: `nothing matches ${rootSelector}` }];
  const parse = (text) => {
    const match = /rgba?\\(([^)]+)\\)/.exec(text || "");
    if (!match) return null;
    const parts = match[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number);
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const over = (top, bottom) => ({
    r: top.r * top.a + bottom.r * (1 - top.a),
    g: top.g * top.a + bottom.g * (1 - top.a),
    b: top.b * top.a + bottom.b * (1 - top.a),
    a: 1,
  });
  const luminance = ({ r, g, b }) => {
    const channel = (value) => {
      const v = value / 255;
      return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  };
  const behind = (element) => {
    const layers = [];
    for (let node = element; node; node = node.parentElement) {
      const colour = parse(getComputedStyle(node).backgroundColor);
      if (colour && colour.a > 0) {
        layers.push(colour);
        if (colour.a >= 1) break;
      }
    }
    let colour = { r: 255, g: 255, b: 255, a: 1 };
    for (let index = layers.length - 1; index >= 0; index -= 1) colour = over(layers[index], colour);
    return colour;
  };
  const shown = (element) => {
    const style = getComputedStyle(element);
    if (style.visibility !== "visible" || Number(style.opacity) === 0) return false;
    if (element.closest("[hidden], [aria-hidden='true']")) return false;
    const box = element.getBoundingClientRect();
    // Visually hidden text (the sr-only pattern) is 1 px and clipped.
    return box.width > 1 && box.height > 1 && style.clip !== "rect(0px, 0px, 0px, 0px)";
  };
  const failures = [];
  const seen = new Set();
  const controls = "input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=range]):not([type=color]), select, textarea, button";
  const candidates = [...root.querySelectorAll("*")].filter((element) => (
    element.matches(controls)
    || [...element.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim())
  ));
  for (const element of candidates) {
    if (seen.size >= limit || !shown(element) || element.disabled) continue;
    seen.add(element);
    const style = getComputedStyle(element);
    const background = behind(element);
    const text = parse(style.color);
    if (!text) continue;
    const foreground = over(text, background);
    const [light, dark] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
    const ratio = (light + 0.05) / (dark + 0.05);
    const size = parseFloat(style.fontSize);
    const large = size >= 24 || (size >= 18.66 && Number(style.fontWeight) >= 700);
    const needed = large ? 3 : 4.5;
    if (ratio + 1e-6 < needed) {
      const label = (element.value || element.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 60);
      failures.push({
        element: `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ""}${element.className && typeof element.className === "string" ? `.${element.className.trim().split(/\\s+/).join(".")}` : ""}`,
        text: label,
        ratio: Math.round(ratio * 100) / 100,
        needed,
        color: style.color,
        background: `rgb(${Math.round(background.r)}, ${Math.round(background.g)}, ${Math.round(background.b)})`,
      });
    }
  }
  return failures;
}
"""

# Tab from the last control leaves the page for the browser's own toolbar; the
# page sees that as focus on <body>, so it is reported as the end of the page.
_FOCUS_JS = """
async () => {
  const element = document.activeElement;
  if (!element) return { problem: "nothing has focus" };
  if (element === document.body) return { name: "the end of the page", end: true, visible: true };
  const frame = () => new Promise((resolve) => requestAnimationFrame(resolve));
  await frame();
  await frame();
  const style = getComputedStyle(element);
  const box = element.getBoundingClientRect();
  const outline = style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0;
  const ring = style.boxShadow && style.boxShadow !== "none";
  const onScreen = box.bottom > 0 && box.top < window.innerHeight && box.right > 0 && box.left < window.innerWidth;
  const name = `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ""}${element.name ? `[name=${element.name}]` : ""}`;
  return {
    name, visible: (outline || ring) && onScreen && box.width > 0 && box.height > 0, outline: style.outline, ring: style.boxShadow,
    box: [box.left, box.top, box.width, box.height].map(Math.round), window: [window.innerWidth, window.innerHeight],
  };
}
"""

_TARGETS_JS = """
([rootSelector, minimum]) => {
  const root = document.querySelector(rootSelector);
  const small = [];
  for (const element of root.querySelectorAll("button, select, input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea")) {
    const box = element.getBoundingClientRect();
    if (box.width <= 1 || box.height <= 1 || element.closest("[hidden]")) continue;
    if (box.width + 0.5 < minimum || box.height + 0.5 < minimum) {
      small.push(`${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ""} ${Math.round(box.width)}x${Math.round(box.height)} "${(element.textContent || element.name || "").trim().slice(0, 30)}"`);
    }
  }
  return small;
}
"""


def contrast_failures(page: Any, root: str = "body", limit: int = 3000) -> list[dict[str, Any]]:
    """Text and controls under ``root`` with less contrast than WCAG AA asks."""
    return page.evaluate(_CONTRAST_JS, [root, limit])


def sideways_scroll(page: Any) -> int:
    """How many CSS px the page is wider than the window (0 when it fits)."""
    return page.evaluate("() => Math.max(0, document.documentElement.scrollWidth - window.innerWidth)")


def small_targets(page: Any, root: str = "body", minimum: int = 24) -> list[str]:
    """Buttons and fields under ``root`` smaller than ``minimum`` CSS px either way."""
    return page.evaluate(_TARGETS_JS, [root, minimum])


def stop_smooth_scrolling(page: Any) -> None:
    """Scroll instantly from here on, until the page reloads.

    The page scrolls smoothly (lab.css), so each focus scroll is animated, and one
    still running can carry the page away from the control that has focus now.
    With it off, every focus scroll lands at once and a check measures where it
    ends, as a reader sees it once the page stops moving. (Emulating reduced motion
    would do the same, but lab.css then gives every property a 0.01 ms transition,
    and colours read mid-switch.) Call it right after the page opens; scrolls the
    page's own scripts ask for stay smooth, so see ``wait_until_still``.
    """
    page.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; }")


# The page's own scripts scroll smoothly too (to a new result, say), and such a
# scroll can still be running when a test starts checking. Done once no scroll
# event has fired, on the page or any panel in it, for ``quietMs``.
_STILL_JS = """
async (quietMs) => {
  let last = performance.now();
  const moved = () => { last = performance.now(); };
  window.addEventListener("scroll", moved, true);
  const started = performance.now();
  try {
    while (performance.now() - last < quietMs) {
      if (performance.now() - started > 5000) return false;
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    return true;
  } finally {
    window.removeEventListener("scroll", moved, true);
  }
}
"""


def wait_until_still(page: Any, quiet_ms: int = 400) -> None:
    """Wait until the page has stopped scrolling; fail if it keeps scrolling for 5 s."""
    assert page.evaluate(_STILL_JS, quiet_ms), "the page kept scrolling for 5 s"


def tab_through(page: Any, presses: int) -> list[dict[str, Any]]:
    """Press Tab up to ``presses`` times; return where focus went and whether it showed.

    Stops early at the end of the page, where the next Tab would leave it.
    """
    stop_smooth_scrolling(page)
    stops = []
    for _ in range(presses):
        page.keyboard.press("Tab")
        stops.append(page.evaluate(_FOCUS_JS))
        if stops[-1].get("end"):
            break
    return stops


# Should a colour ever change with a CSS transition, the page reports the old
# theme's colour until it ends, so the switch waits for every transition it starts.
_THEME_JS = """
async (theme) => {
  document.documentElement.dataset.theme = theme;
  getComputedStyle(document.body).color;
  const changing = document.getAnimations().filter((animation) => animation instanceof CSSTransition);
  await Promise.all(changing.map((animation) => animation.finished.catch(() => null)));
  await new Promise((resolve) => requestAnimationFrame(resolve));
}
"""


def set_theme(page: Any, theme: str) -> None:
    """Show the page in the light or dark theme, as the theme picker does, once its colours have settled."""
    page.evaluate(_THEME_JS, theme)
