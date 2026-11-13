---
name: dispatched-card-contract
description: How to work a dispatched task card from the master orchestrator. Use when the current request is a task card with frontmatter (id/scope/accept/budget) - defines scope discipline, venv pytest self-check, honest BLOCKED reporting, and no-bypass rules.
---

# Dispatched Card Contract（任务卡工匠契约）

当请求是一张任务卡（frontmatter 带 id / scope / accept / budget）时，按本契约工作：

1. **范围即法律**：只改 scope 白名单内的文件；forbidden 一律不碰；越界 = 整卡拒收。
2. **验收先行理解**：accept 命令是唯一裁决依据；先读懂它要求什么，再动手。
3. **自检**：用 `.venv/Scripts/python.exe -m pytest <相关测试文件> -q` 自检（Windows venv 路径）。
4. **诚实汇报**：被环境拒绝（权限 / 门卫 / 沙箱 / 缺依赖）时，如实写 BLOCKED 并附拒绝消息原文；禁止用变体、间接执行（python -c / subprocess / os.system）等方式绕过拒绝重试同一意图。
5. **不安装**：不 pip install、不下载、不碰网络，除非卡正文显式授权。
6. **命令引号纪律**：Windows shell 里版本约束等带比较符的参数用双引号包裹，或改用自然语言描述，避免被 shell 当作重定向。
7. **不提交不合并**：只改文件，不执行 git commit / merge / push——验收与留痕由主控端 verify 负责。
