const {spawn} = require("node:child_process");
const {join} = require("node:path");

exports.name = "my-skill-library-panel";

exports.apply = function apply(ctx) {
  return ctx.effect(() => {
    const child = spawn("python", ["-B", join(__dirname, "..", "mcp_server.py"), "--serve"], {
      env: {...process.env, SKILL_LIBRARY_PORT: "18765"},
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    child.stdout.resume();
    child.stdin.on("error", error => console.error("[my-skill-library]", error.message));
    child.stderr.on("data", data => console.error("[my-skill-library]", data.toString().trim()));
    child.on("error", error => console.error("[my-skill-library]", error.message));
    return () => child.stdin.end();
  });
};
