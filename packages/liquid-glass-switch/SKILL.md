---
name: liquid-glass-switch
description: Add or adapt a draggable liquid-glass segmented switch in a web app or AI coding harness UI. Use when implementing two-option view or mode controls with a moving glass lens, drag threshold, bounded elastic overscroll, or plane/sphere transitions.
license: MIT
---

# Liquid Glass Switch for Harness UIs

Use this skill when a user asks to add the packaged glass switch to a web interface, an AI coding harness, or a similar project UI. The goal is to adapt the component to the host project's framework and state model, not to redesign unrelated parts of the harness.

## Workflow

1. Inspect the host project before editing. Find the UI entry point, framework, existing segmented controls, state owner, styling approach, and available build or preview commands. Follow its local `AGENTS.md`, `CLAUDE.md`, and other project instructions.
2. Identify the pair of states the user wants to switch. This component is for exactly two choices, such as Plane/Sphere or Global/Local. If the user asks for more choices, explain that the packaged control is binary and adapt it only if the requested interaction still makes sense.
3. Read `references/harness-porting.md` and the source files next to this skill. Start from `liquid-controls.js` and `liquid-controls.css`; reuse them directly when their DOM contract fits. Otherwise port their interaction model into the host framework.
4. Connect selection to the host's actual state source. A click or drag must update both the selected visual state and the displayed view. In declarative frameworks, derive the active styling and `aria-pressed` from framework state instead of mutating the DOM behind the framework's back.
5. Preserve the key interaction behavior: continuous pointer dragging, repeated direction reversals during one gesture, switch at the 70% travel threshold, settle at the selected option, and cap lens overhang at 20 CSS pixels per side. Respect `prefers-reduced-motion`.
6. Scope or rename CSS selectors if the host app already uses `.view-switch`, `.view-button`, or `.view-lens`. Avoid changing the harness's unrelated navigation, panels, routing, or persistence.
7. Verify the actual host UI with its available build, test, or browser preview workflow. Check mouse and touch dragging, direct button activation, reversed/fast gestures, resize, keyboard focus, and reduced motion. Report which checks were run and any limitation in the host harness.

## Packaged resources

- `liquid-controls.js`: dependency-free pointer and lens animation behavior.
- `liquid-controls.css`: light and dark glass appearance.
- `demo.html`: standalone browser example.
- `README.md`: vanilla HTML quick start and tuning notes.
- `references/harness-porting.md`: framework and harness integration guidance.

The switch uses native buttons. The host project remains responsible for changing the selected state in response to the buttons' normal `click` events.
