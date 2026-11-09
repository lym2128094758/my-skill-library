# Liquid Glass Switch

A dependency-free, two-option segmented switch with an Apple-inspired frosted-glass lens. Drag the lens to switch options, including repeated direction changes in one gesture. The lens follows the pointer with a bounded elastic overhang (20 px maximum), then settles onto the active option. It also supports reduced-motion preferences and keyboard-accessible native buttons.

This folder also includes an installable Agent Skill (`SKILL.md`). Coding agents that support the Agent Skills format can use it to adapt the component to their host app or AI coding harness. Agents without skill support can still use the source and integration notes directly from this GitHub folder.

## Quick start

Copy `liquid-controls.js` and `liquid-controls.css` into your project, then use this markup:

```html
<div class="view-switch" role="group" aria-label="Display mode">
  <button class="view-button active" type="button" aria-pressed="true">Plane</button>
  <button class="view-button" type="button" aria-pressed="false">Sphere</button>
</div>
<link rel="stylesheet" href="liquid-controls.css">
<script defer src="liquid-controls.js"></script>
```

The script adds the moving lens automatically. On each button's normal `click` handler, update `.active` and `aria-pressed` to match the selected option; the lens observes the active class and animates to it. Each control must contain exactly two `.view-button` elements.

The switch emits ordinary button clicks, so connect those buttons to whatever view or state your app controls. No framework or dependency is required.

## Theme

The default style is a bright translucent glass capsule. Add `data-theme="dark"` to the switch for the dark glass appearance:

```html
<div class="view-switch" data-theme="dark" role="group" aria-label="Display mode">
```

Override CSS custom properties or the component classes to match your design. Keep the switch positioned so its 20 px elastic overhang is not clipped by an ancestor (`overflow: visible`).

## Demo

Open `demo.html` directly in a browser. It demonstrates two independent switches and both light and dark themes.

## Use with an AI coding agent

Give your coding agent this folder or the GitHub link and ask it to install/use the `liquid-glass-switch` skill while adapting the switch to your harness. For platforms that load Agent Skills from a local directory, place this folder in the platform's skills directory. For Claude's uploaded skills, zip this folder so the ZIP contains `liquid-glass-switch/SKILL.md` and the component files. If the agent does not support skills, include `SKILL.md` and `references/harness-porting.md` in the prompt context.

## Configuration

The current elastic overhang limit is `20` CSS pixels per side. Change the `maxOverflow` constant in `liquid-controls.js` to adjust it. The lens uses a 70% drag threshold to select the other option; this is configurable as the `0.7` threshold in the same file.

## License

MIT
