(() => {
  "use strict";

  const pending = new Map();
  const profiles = new Map();
  let nextId = 0;
  let context = {};
  const parent = window.parent;

  function post(message) {
    parent.postMessage({jsonrpc: "2.0", ...message}, "*");
  }

  function request(method, params, timeout = 35000) {
    return new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error("宿主未响应图谱请求。"));
      }, timeout);
      pending.set(id, {resolve, reject, timer});
      post({id, method, params});
    });
  }

  const expand = document.getElementById("expandGraph");
  function updateContext(next) {
    context = {...context, ...next};
    const full = context.displayMode === "fullscreen";
    expand.hidden = !context.availableDisplayModes?.includes(full ? "inline" : "fullscreen");
    expand.setAttribute("aria-label", full ? "退出全屏" : "应用内全屏");
    expand.title = expand.getAttribute("aria-label");
  }

  window.addEventListener("message", ({source, data}) => {
    if (source !== parent || data?.jsonrpc !== "2.0") return;
    const call = pending.get(data.id);
    if (call && ("result" in data || "error" in data)) {
      pending.delete(data.id);
      clearTimeout(call.timer);
      if (data.error) call.reject(new Error(data.error.message));
      else call.resolve(data.result);
    } else if (data.method === "ui/notifications/host-context-changed") {
      updateContext(data.params);
    } else if (data.method === "ping" || data.method === "ui/resource-teardown") {
      post({id: data.id, result: {}});
    }
  });

  const ready = request("ui/initialize", {
    protocolVersion: "2026-01-26",
    appInfo: {name: "my-skill-library", version: "1.1.0"},
    appCapabilities: {availableDisplayModes: ["inline", "fullscreen"]},
  }, 10000).then(result => {
    updateContext(result.hostContext);
    post({method: "ui/notifications/initialized", params: {}});
    post({method: "ui/notifications/size-changed", params: {height: 620}});
  });

  expand.addEventListener("click", async () => {
    const mode = context.displayMode === "fullscreen" ? "inline" : "fullscreen";
    if (!context.availableDisplayModes?.includes(mode)) return;
    try {
      const result = await request("ui/request-display-mode", {mode});
      updateContext({displayMode: result.mode});
    } catch (error) {
      expand.title = error.message;
    }
  });

  window.skillLibraryStorage = {
    getItem(key) {
      try { return window.localStorage.getItem(key); }
      catch { return profiles.get(key) ?? null; }
    },
    setItem(key, value) {
      profiles.set(key, value);
      try { window.localStorage.setItem(key, value); } catch {}
    },
  };

  window.skillLibraryFetch = async (path, options = {}) => {
    await ready;
    options.signal?.throwIfAborted();
    const url = new URL(path, "https://skill-library.invalid");
    let name, args = {};
    if (url.pathname === "/api/skills") name = "graph_snapshot";
    else if (url.pathname === "/api/skill") {
      name = "get_skill";
      args = {id: url.searchParams.get("id")};
    } else if (url.pathname === "/api/relations" && options.method === "POST") {
      name = "set_manual_relation";
      args = {...JSON.parse(options.body), action: "add"};
    } else {
      throw new Error("图谱请求不受支持。");
    }
    const result = await request("tools/call", {name, arguments: args});
    options.signal?.throwIfAborted();
    const content = result.content?.find(item => item.type === "text")?.text;
    const data = result.isError ? {error: content} : result.structuredContent ?? JSON.parse(content);
    return {ok: !result.isError, json: async () => data};
  };
})();
