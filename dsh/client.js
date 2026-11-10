window.__ModuleLoader__.load({
  id: "dsh-my-skill-library",
  factory(require) {
    const React = require("react");
    const h = React.createElement;

    function SkillLibraryPanel() {
      const [open, setOpen] = React.useState(false);
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
            padding: "7px 12px", border: "1px solid #9ba9a3", borderRadius: 18,
            background: "#eff4f1", color: "#23372c", cursor: "pointer",
          },
        }, "Skill 图谱"),
        open && h("section", {
          "aria-label": "我的 Skill 图谱",
          role: "dialog",
          style: {
            position: "fixed", top: "max(36px, var(--dsh-frame-overlay-top, 36px))",
            right: 24, bottom: 24, left: 24, zIndex: 10000,
            display: "flex", flexDirection: "column", background: "#fff",
            border: "1px solid #cbd1d4", borderRadius: 12, overflow: "hidden",
            boxShadow: "0 16px 64px #0004",
          },
        },
          h("div", {style: {display: "flex", justifyContent: "space-between", padding: "8px 14px", color: "#262725"}},
            h("strong", null, "我的 Skill 图谱"),
            h("button", {type: "button", onClick: () => setOpen(false), "aria-label": "关闭图谱"}, "×")),
          h("iframe", {
            src: "http://127.0.0.1:18765",
            title: "二维与三维 Skill 图谱",
            sandbox: "allow-scripts allow-same-origin",
            allow: "clipboard-write",
            referrerPolicy: "no-referrer",
            style: {border: 0, flex: 1, width: "100%", minHeight: 0, background: "#fff"},
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
