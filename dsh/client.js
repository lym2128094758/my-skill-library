window.__ModuleLoader__.load({
  id: "dsh-my-skill-library",
  factory(require) {
    const React = require("react");
    const h = React.createElement;

    function SkillLibraryPanel() {
      const [open, setOpen] = React.useState(false);
      const frame = React.useRef(null);
      function sendTheme() {
        const style = getComputedStyle(document.body);
        const tokens = {
          "--color-background-primary": "--dsw-alias-bg-base",
          "--color-background-secondary": "--dsw-alias-bg-layer-1",
          "--color-background-tertiary": "--dsw-alias-bg-layer-2",
          "--color-text-primary": "--dsw-alias-label-primary",
          "--color-text-secondary": "--dsw-alias-label-secondary",
          "--color-border-primary": "--dsw-alias-border-l2",
          "--color-text-info": "--dsw-alias-state-business-primary",
          "--font-sans": "--dsw-font-family",
        };
        const variables = {};
        for (const [key, token] of Object.entries(tokens)) {
          const value = style.getPropertyValue(token).trim();
          if (value) variables[key] = value;
        }
        const theme = document.body.hasAttribute("data-ds-dark-theme") ? "dark" : "light";
        frame.current?.contentWindow?.postMessage({
          type: "skill-library-theme", context: {theme, styles: {variables}},
        }, "http://127.0.0.1:18769");
      }
      React.useEffect(() => {
        if (!open) return;
        const observer = new MutationObserver(sendTheme);
        for (const element of [document.body, document.documentElement]) {
          observer.observe(element, {attributes: true, attributeFilter: ["style", "class", "data-ds-dark-theme"]});
        }
        return () => observer.disconnect();
      }, [open]);
      React.useEffect(() => {
        if (!open) return;
        const closeOnEscape = event => {
          if (event.key === "Escape") setOpen(false);
        };
        window.addEventListener("keydown", closeOnEscape);
        return () => window.removeEventListener("keydown", closeOnEscape);
      }, [open]);
      return h(React.Fragment, null,
        h("button", {
          type: "button",
          onClick: () => setOpen(value => !value),
          "aria-expanded": open,
          style: {
            position: "fixed", right: 20, bottom: 18, zIndex: 9999,
            padding: "7px 12px", border: "1px solid var(--dsw-alias-border-l2, #d4d4d8)", borderRadius: 18,
            background: "var(--dsw-alias-button-floating-fill, Canvas)",
            color: "var(--dsw-alias-label-primary, CanvasText)", cursor: "pointer",
            font: "inherit", boxShadow: "var(--dsw-elevation-soft, 0 2px 8px #0000000a)",
          },
        }, "Skill 图谱"),
        open && h("section", {
          "aria-label": "我的 Skill 图谱",
          role: "dialog",
          style: {
            position: "fixed", top: "max(36px, var(--dsh-frame-overlay-top, 36px))",
            right: 24, bottom: 24, left: 24, zIndex: 10000,
            display: "flex", flexDirection: "column", background: "var(--dsw-alias-bg-base, Canvas)",
            border: "1px solid var(--dsw-alias-border-l2, #d4d4d8)", borderRadius: 12, overflow: "hidden",
            boxShadow: "0 16px 64px #0004",
          },
        },
          h("div", {style: {display: "flex", justifyContent: "space-between", padding: "8px 14px", color: "var(--dsw-alias-label-primary, CanvasText)"}},
            h("strong", null, "我的 Skill 图谱"),
            h("button", {
              type: "button", onClick: () => setOpen(false), "aria-label": "关闭图谱",
              style: {border: 0, background: "transparent", color: "inherit", cursor: "pointer"},
            }, "×")),
          h("iframe", {
            ref: frame,
            onLoad: sendTheme,
            src: "http://127.0.0.1:18769",
            title: "二维与三维 Skill 图谱",
            sandbox: "allow-scripts allow-same-origin",
            allow: "clipboard-write",
            referrerPolicy: "no-referrer",
            style: {border: 0, flex: 1, width: "100%", minHeight: 0, background: "var(--dsw-alias-bg-base, Canvas)"},
          })));
    }

    return {
      inject: ["slots"],
      apply(ctx) {
        ctx.slots.inject("shell.overlay", () => ctx.slots.register({
          name: "shell.overlay", id: "my-skill-library", order: 5,
        }, SkillLibraryPanel));
      },
    };
  },
});
