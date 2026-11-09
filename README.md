# 我的 Skill 库 · My Skill Library

作者：[lym2128094758](https://github.com/lym2128094758)

仓库：https://github.com/lym2128094758/my-skill-library

一个在自己电脑上运行的 Skill 浏览器，以类似 Obsidian 的可拖动圆点关系图展示自己的 Skill 库。每个节点对应一个 `SKILL.md`，连线来自正文提及、手动关联或可选的主题推测。点击节点可以查看说明、原文件路径和完整正文。

本项目读取已有 Skill 目录，不需要把 Skill 复制进仓库。当前功能是浏览、展示和管理关联；没有执行 Skill、调用模型、安装 Skill、编辑原 Skill 或自动同步云端的接口。

## 1. 直接启动

需要 Python 3.10+ 和现代浏览器。后端只用 Python 标准库，前端是原生 JavaScript、SVG 和已随仓库提供的 D3，不需要 Node.js、npm install 或前端构建。

```powershell
git clone https://github.com/lym2128094758/my-skill-library.git
cd my-skill-library
python server.py
```

Windows 也可以双击 `start.bat`。启动后打开 <http://127.0.0.1:8765>，按 Ctrl+C 停止。仓库当前为私有时，克隆需要你的 GitHub 账号有访问权限。

第一次启动会从 `config.example.json` 自动创建 `config.json`。默认扫描 `~/.codex/skills`。如果没有节点，先编辑配置，再点击页面右上角刷新按钮。修改监听地址或端口后需要重启服务。

## 2. 配置自己的 Skill 库

`config.json` 示例：

```json
{
  "skill_roots": [
    "~/.codex/skills",
    "D:/my-skills"
  ],
  "host": "127.0.0.1",
  "port": 8765
}
```

| 字段 | 含义 |
| --- | --- |
| `skill_roots` | 要递归扫描的目录数组。只读取文件名为 `SKILL.md` 的文件；不存在的目录跳过。 |
| `host` | 默认 `127.0.0.1`，供本机访问。 |
| `port` | 默认 `8765`；端口被占用时换一个端口。 |

路径支持 `~`、系统环境变量（Windows 可用 `%USERPROFILE%`），相对路径以项目根目录为基准。JSON 中 Windows 路径建议用 `/`；使用反斜杠时需写成 `\\`。示例配置使用 `~`，适合跨平台。

最小 Skill 示例，可放在任一扫描目录下的 `my-example/SKILL.md`：

```markdown
---
name: my-example
description: 演示自己的 Skill
---
# 使用方式
需要画图时参考 figure-designer。
```

`name` 缺失时使用所在文件夹名，`description` 缺失时显示“暂无说明”。解析器只支持常用的简单 frontmatter 和缩进多行描述，并非完整 YAML 解析器。重复配置同一个文件时按解析后的路径去重。

## 3. 页面怎么用

- 拖动圆点移动节点，松开后继续参与力场运动；拖动空白平移，滚轮缩放，右下角按钮重新居中。节点坐标不会保存。
- 点击节点查看说明、路径、相邻 Skill 和正文；正文以纯文本展示。选择节点后可切换局部图，展开 1–5 层邻居。
- 搜索支持普通关键词、`name:`、`path:`、`source:`、双引号短语和 `-排除词`。例如 `source:个人技能 -name:example`。多条件取交集，不支持正则或 OR。
- 来源筛选、搜索和连线类型共同决定当前子图；局部图在筛选后的图上查找邻居。“孤立节点”也是按当前可见连线判断。
- 齿轮设置可调整来源颜色、名称显现阈值、节点大小、连线粗细、引用箭头、中心引力、排斥力、连线强度和距离。
- 点击“建立关联”，依次点两个节点，保存无向手动关联。删除目前通过 API 或停止服务后编辑 `data/relations.json` 完成。
- `/` 定位搜索，`Esc` 关闭面板或取消连线，`+`、`-` 缩放，方向键平移，Shift 加速。

浏览器 `localStorage` 保存图谱设置和颜色，键名为 `skill-graph-settings-v2`、`skill-graph-colors-v2`。设置与浏览器来源（协议、地址、端口）绑定，不会保存到服务端。搜索、选中项和隐藏分组不持久化。

## 4. 图谱里的关系是什么意思

| `kind` | 来源与含义 | 默认显示 |
| --- | --- | --- |
| `mention` | Skill 正文明确提及另一个 Skill 的名称或文件夹名；保留提及方向。 | 是 |
| `manual` | 用户用页面或 API 手动建立的无向关联。 | 是 |
| `topic` | 根据名称和描述的词汇重合计算的无向建议，不能当作真实依赖。 | 否 |

正文匹配排除 frontmatter，别名长度至少为 4。含连字符的名字按词边界匹配；普通词名需用反引号、双中括号或路径片段明确提及。同名候选优先匹配同组唯一目标，仍有歧义则不连线；同名 Skill 之间不自动连接。实现入口是 `reference_edges()`。

主题建议使用英文词和中文片段，对常见词降权，要求至少两个共享词且加权交并比达到 0.12，每个节点最多选两个候选；由于另一端也可能选中它，最终度数可能超过 2。已有正文提及的节点对不会再生成主题边。

节点 ID 是解析后绝对路径小写字符串的 SHA-1 前 14 位。名称相同、路径不同的 Skill 可以有不同 ID；同一路径改正文不改变 ID。移动文件或换电脑可能改变 ID，因此手动关系不能保证跨电脑直接复用。

API 返回原始关系。同一对节点可同时有正文边和手动边；页面会合并为一条可见连线，并保留全部类型，颜色优先级为手动 > 正文 > 主题。API `edges.length` 因此可能大于页面显示的连线数。`source`、`group` 是后端依据来源目录生成的展示分组，不等同于 Skill frontmatter 标签。

## 5. HTTP API（给其他 AI / 脚本接入）

默认根地址：`http://127.0.0.1:8765`。API 版本 `1.0.0`。机器可读契约见仓库 [openapi.json](openapi.json)，运行时也可读取 `GET /api/openapi.json`。当前 API 不要求 Token，供本机脚本和同源页面调用；没有配置跨域 CORS，也没有 Skill 执行接口。由于接口可以读取本机 Skill 正文，请保持默认本机监听。

### 接口总览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 返回进程可用状态与 API 版本；不扫描文件，不代表扫描一定成功。 |
| GET | `/api/skills` | 重新扫描所有来源，返回未经过页面筛选的节点、全部边和手动边。 |
| GET | `/api/skill?id=<id>` | 按当前 ID 返回节点和原始 `SKILL.md` 正文。 |
| GET | `/api/relations` | 返回持久化的手动边，包括来源文件移走后失效的 ID。 |
| POST | `/api/relations` | 创建无向手动边；重复创建幂等。 |
| DELETE | `/api/relations` | 删除无向手动边；不存在时也成功，可清理失效 ID。 |
| GET | `/api/openapi.json` | 返回 OpenAPI 3.0.3 接口契约。 |

没有服务端分页、搜索、文件监听或扫描缓存。`GET /api/skills` 每次扫描，详情查询和创建关联也会扫描以验证 ID；UI 搜索和局部图计算在浏览器执行。大库的主题匹配有成对比较成本，目前适合个人本地库。

### 返回数据

`GET /api/health`：

```json
{"ok": true, "api_version": "1.0.0"}
```

`GET /api/skills` 示例（ID 和路径为示意）：

```json
{
  "nodes": [
    {"id":"aaaaaaaaaaaaaa","name":"alpha-skill","slug":"alpha-skill","description":"示例 A","source":"my-skills","group":"my-skills","path":"D:/my-skills/alpha-skill/SKILL.md"},
    {"id":"bbbbbbbbbbbbbb","name":"beta-skill","slug":"beta-skill","description":"示例 B","source":"my-skills","group":"my-skills","path":"D:/my-skills/beta-skill/SKILL.md"}
  ],
  "edges": [{"source":"aaaaaaaaaaaaaa","target":"bbbbbbbbbbbbbb","kind":"mention","forward":true,"backward":false}],
  "manual": []
}
```

节点字段：`id` 是接口使用的标识；`name` 是 frontmatter 名称或文件夹名；`slug` 是文件夹名；`description` 是简介；`source`、`group` 是展示来源和分组；`path` 是原文件绝对路径。列表不返回正文。

边的 `source` / `target` 按 ID 字典序排序，不能直接把 `source` 当成“发起引用的人”。正文边的 `forward=true` 表示 source 提及 target，`backward=true` 表示 target 提及 source，两者可同时成立。主题边和手动边不含方向字段。`manual` 是 `edges` 中手动边的单独副本，客户端不要再把它重复追加到 `edges`。

`GET /api/skill?id=...` 返回 `{"node": <上述节点对象>, "content": "完整 Markdown 正文"}`。`GET /api/relations` 返回 `{"relations": [<手动边>]}`。失效的手动边保留在存储和 API 中，页面会忽略不存在的节点 ID。

POST 和 DELETE 都要求 `Content-Type: application/json`，请求体为：

```json
{"source": "aaaaaaaaaaaaaa", "target": "bbbbbbbbbbbbbb"}
```

成功均返回 HTTP 200：

```json
{"ok": true, "relation": {"source":"aaaaaaaaaaaaaa","target":"bbbbbbbbbbbbbb","kind":"manual"}, "changed": true}
```

`changed` 表示持久化数据是否实际改变。两端颠倒视为同一条边，重复创建或重复删除返回 `changed=false`。禁止自连；创建时必须使用当前 `/api/skills` 返回的 ID。删除只移除手动边，同一节点对仍可能存在自动边。删除后应重新获取图谱；页面不会自动感知外部脚本写入，需要点击刷新。

### 可直接运行的 PowerShell 示例

先启动服务，在另一个 PowerShell 中执行：

```powershell
$base = 'http://127.0.0.1:8765'
Invoke-RestMethod "$base/api/health"
$graph = Invoke-RestMethod "$base/api/skills"
$graph.nodes | Select-Object id, name, source, path
if ($graph.nodes.Count -gt 0) {
    $id = $graph.nodes[0].id
    Invoke-RestMethod "$base/api/skill?id=$id"
}
```

以下示例会创建两个真实节点间的手动边。删除语句保留为注释，按需要执行：

```powershell
if ($graph.nodes.Count -lt 2) { throw '至少需要两个 Skill' }
$body = @{ source = $graph.nodes[0].id; target = $graph.nodes[1].id } | ConvertTo-Json
Invoke-RestMethod "$base/api/relations" -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod "$base/api/relations"
# Invoke-RestMethod "$base/api/relations" -Method Delete -ContentType 'application/json' -Body $body
```

Python 读取示例（不依赖 requests）：

```python
import json
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8765/api/skills", timeout=30) as response:
    graph = json.load(response)
for node in graph["nodes"]:
    print(node["id"], node["name"], node["path"])
```

### 错误约定

已实现接口的错误统一返回 JSON：`{"ok": false, "error": "错误说明"}`。客户端先检查 HTTP 状态码，再读取 `error`，不要匹配具体英文文案。

| 状态码 | 情况 |
| --- | --- |
| 400 | 缺少 id、非法 JSON、请求体不是对象、端点不是非空字符串、自连或创建时 ID 不存在。 |
| 404 | 详情 ID 不存在，或在 GET/POST/DELETE 下请求未知 `/api/` 路径。 |
| 413 | 写入请求体超过 65,536 字节。 |
| 415 | POST/DELETE 的 Content-Type 不是 application/json。 |
| 500 | 配置、文件读写等服务端错误。 |

静态文件错误和未实现的 HTTP 方法仍由 Python 标准 HTTP 服务处理，不保证返回上述 JSON。

## 6. 文件与模块地图

```text
my-skill-library/
├─ server.py                 # 扫描、frontmatter、关系推导、HTTP API、静态文件服务
├─ config.example.json       # 可提交的通用配置
├─ config.json               # 自动生成的本机配置，Git 忽略
├─ openapi.json              # API 契约，接口变更时同步维护
├─ start.bat                 # Windows 启动入口
├─ data/relations.json       # 持久化手动边，当前由 Git 跟踪
├─ web/
│  ├─ index.html             # 页面结构和控件
│  ├─ styles.css             # 布局和样式
│  ├─ app.js                 # 数据请求、D3 力场、交互、详情和设置
│  ├─ graph-model.js         # 搜索、边合并、子图过滤、标签透明度纯函数
│  └─ vendor/d3.min.js        # 本地 D3
├─ tests/                    # 关系推导、HTTP API、图模型测试
└─ D3-LICENSE.txt            # 第三方 D3 许可与原作者署名
```

数据流：`config.json → scan_skills() → 节点 + 正文边 + 主题边 → 合并 data/relations.json → /api/skills → graph-model.js 筛选与合并 → app.js 的 D3 + SVG 渲染`。`/api/skill` 单独按需读取正文。

力场使用 D3 的中心方向吸引（forceX / forceY）、节点排斥（forceManyBody）、碰撞避让（forceCollide）和连线弹簧（forceLink）。页面中的圆形点云是动态力场结果，没有固定圆形排布或永久固定节点。

修改关系识别请看 `reference_edges()` / `scan_skills()`；修改图谱过滤请看 `graph-model.js`；修改交互和力场请看 `app.js` 的 `configureForces()`、`rebuild()`、`selectNode()`；新增 API 请改 `Handler` 并同步 `openapi.json`、本文和接口测试。

## 7. 交给另一个 AI 的接手说明

可以把下面这段连同 README 一起发给其他 AI：

> 这是我的个人 Skill 图谱项目，作者 lym2128094758。先阅读 README、server.py、web/graph-model.js、web/app.js 和 openapi.json，以代码中的现状为准。技术栈是 Python 标准库 HTTP 服务 + 原生 JS + 本地 D3/SVG，无需 npm 构建。Skill 源目录在本机 config.json 中，原文件只读，手动边存放 data/relations.json，图谱设置存放浏览器 localStorage。请在现有项目内继续修改；按目标功能查对应模块，接口变更同步 OpenAPI 和调用示例。不要把图谱展示理解为执行 Skill，也不要把主题建议理解为真实依赖。先说明实际要改的文件，完成后运行相关检查并报告结果。如果你访问不了私有 GitHub 仓库，需要我提供代码或授予访问权限。

换电脑使用时：克隆仓库 → 运行 `python server.py` → 修改自动生成的配置路径 → 刷新图谱。仅提供 GitHub 链接不能保证其他 AI 有私有仓库访问权限；可以直接粘贴本文，或提供项目源文件。原 Skill 文件不包含在这个仓库中，需要在目标电脑另行准备。

## 8. 开发检查与常见问题

```powershell
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/graph-model.test.cjs
node --check web/app.js
```

运行前端测试才需要 Node.js；正常启动应用只需要 Python。HTTP 测试使用临时 Skill 目录和随机端口，不写入你的真实手动关系文件。

- **页面打不开**：确认服务终端仍在运行、地址与 config 的端口一致；端口占用时更改 port 并重启。
- **节点为 0**：确认扫描根目录下有 `SKILL.md`，路径展开后存在，文件有读取权限。
- **修改 Skill 后图没变**：点击刷新；没有后台文件监听。
- **移动文件后手动边失效**：路径生成的 ID 已变化，用 DELETE 清理旧边，再用新 ID 建立关联。
- **另一个浏览器样式不同**：图谱设置在各自的 localStorage，可用设置面板恢复默认。
- **发布时要带哪些数据**：本机 config 被忽略，原 Skill 不会复制；`data/relations.json` 目前被 Git 跟踪，后续提交前检查其中是否包含希望分享的个人关联。

## 9. 参考与署名

交互参考 [Obsidian Graph View](https://help.obsidian.md/plugins/graph) 的全局/局部图、孤立节点、分组、悬停聚焦和可调力场。实现结构参考公开的 [Quartz Community Graph](https://github.com/quartz-community/graph)：[`Graph.tsx`](https://github.com/quartz-community/graph/blob/main/src/components/Graph.tsx)、[`graph.inline.ts`](https://github.com/quartz-community/graph/blob/main/src/components/scripts/graph.inline.ts)、[`graph.scss`](https://github.com/quartz-community/graph/blob/main/src/components/styles/graph.scss)。应用代码独立编写。

D3 随项目本地提供，保留 MIT 许可与原作者信息，见 [D3-LICENSE.txt](D3-LICENSE.txt)。项目作者署名为 lym2128094758；第三方依赖保留其原有署名。本仓库尚未为应用代码选择开源许可证。
