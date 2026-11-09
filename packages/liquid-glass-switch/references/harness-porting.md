# Porting the switch into a harness

The packaged widget is a web component pattern implemented with vanilla JavaScript and CSS, not a platform-specific plugin API. A harness can use it wherever it can render DOM and load local styles and scripts. If the harness UI is closed or does not expose its front-end source, this package cannot patch it from the outside.

## DOM contract

The JavaScript finds each `.view-switch`, then reads exactly two `.view-button` elements. One button initially has `.active`. The script inserts a `.view-lens` and animates it to follow the active option. The host must listen for button clicks and update `.active` on the selected button. Keep the `aria-pressed` attribute in sync for assistive technology.

The component intentionally emits ordinary button click events after the drag crosses the switch threshold. This lets the existing application handler update its own state. Do not add a second selection mechanism that competes with that handler.

## Framework adaptation

### React

Keep the selected key in React state. Render `.active` and `aria-pressed` from that key, and set state in `onClick`. Load the component script once after the control is mounted; if controls mount dynamically, initialize newly added controls or adapt the controller into a React hook/component. Do not imperatively toggle classes that React also owns.

### Vue

Use a reactive selected value for the active class and `aria-pressed`, and update it from `@click`. Load/initialize the controller after mount and clean up observers/listeners if the component can be removed and remounted. Avoid direct class mutations that conflict with Vue's bindings.

### Other DOM frameworks or Electron/Tauri harnesses

Keep the project's existing state handler. Include the stylesheet and script in the harness's normal asset pipeline, render the two native buttons, and scope styles to the control. For dynamically mounted views, initialize after mount and disconnect observers/listeners on teardown.

### Canvas or non-DOM renderers

The CSS and script are not a drop-in fit. Reuse the behavior model—continuous pointer position, 70% threshold, reversible selection, capped 20 px overshoot, and settle animation—in the renderer's own input and animation system.

## Adaptation checklist

- [ ] The two labels map to the requested host states.
- [ ] Direct click and drag update the same application state.
- [ ] The moving lens stays inside the viewport, with no ancestor clipping during elastic overhang.
- [ ] Reversing direction repeatedly during one pointer hold selects each crossed option.
- [ ] The lens settles on the current application selection after release.
- [ ] Closing an adjacent panel or switching views does not unintentionally reset the selection.
- [ ] Keyboard activation, visible focus, and reduced-motion preference remain supported.
