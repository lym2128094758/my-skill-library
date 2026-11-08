# 我的 Skill 库

作者：lym2128094758

本地运行的 Skill 浏览与关系图谱。它读取 `config.json` 指定目录中的 `SKILL.md`。默认显示正文提及和手动建立的关联。可在图谱设置里开启根据描述推测的主题关联。

图谱交互参考了 Obsidian 官方 Graph View 的全局/局部视图、孤立节点、分组、悬停聚焦和可调力场；实现结构参考公开的 [Quartz Community Graph](https://github.com/quartz-community/graph) 源码及 [D3 力模拟](https://d3js.org/d3-force)。本项目的应用代码独立编写，D3 依 MIT 许可随项目本地提供，见 `D3-LICENSE.txt`。

参考的代码入口是 Quartz 仓库里的 [`Graph.tsx`](https://github.com/quartz-community/graph/blob/main/src/components/Graph.tsx)、[`graph.inline.ts`](https://github.com/quartz-community/graph/blob/main/src/components/scripts/graph.inline.ts) 和 [`graph.scss`](https://github.com/quartz-community/graph/blob/main/src/components/styles/graph.scss)：分别用于理解配置面、D3 力场/交互和图谱布局。

## 启动

双击 `start.bat`，然后打开 <http://127.0.0.1:8765>。需要 Python 3.10 或更新版本，无需安装第三方依赖。

## 图谱操作

- 拖动圆点移动节点，拖动空白区域平移图谱，滚轮缩放。右下角可以重新居中。
- 左栏可以浏览 Skill、按来源筛选，并使用 `name:`、`path:` 或 `source:` 搜索。按 `/` 定位到搜索框。
- 选择一个节点后切换到局部图，可在图谱设置中展开 1 到 5 层邻居。
- 右上角齿轮可调整颜色组、名称显现阈值、节点大小、连线粗细、引用箭头和布局受力。浏览器会保存这些设置。
- 开启“建立关联”后依次点击两个节点，写入 `data/relations.json`。
- 选择节点可查看说明、原始文件位置和 Skill 正文。

## 管理来源

首次启动会从 `config.example.json` 创建本机的 `config.json`；之后可按需编辑 `skill_roots`。配置支持 `~` 和 `%USERPROFILE%` 路径变量。库只读取这些目录中的 `SKILL.md`；用户建立的关系只写入本项目的 `data/relations.json`。本机配置文件不会提交到 Git。
