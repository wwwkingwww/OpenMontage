#!/usr/bin/env python3
"""工匠 Shell 门卫（P0-1 试点，2026-11-14 大师亲手+留痕）。

经 .cursor/hooks.json 的 beforeShellExecution 挂载：白名单放行
venv pytest 自检与只读 git 查询，其余一律拒绝并留痕。
裁决证据落 master 侧 tasks/_gate/（不污染产品仓 git 状态）。
"""
import json
import os
import re
import sys
import time

LOG = r"E:\TOPVIBECODER\tasks\_gate\openmontage-gate.log"

ALLOW_RES = [
    re.compile(r"^\.?venv[/\\](?:scripts[/\\])?python(?:\.exe)?\s+-m\s+pytest(?:\s|$)", re.I),
    re.compile(r"^python(?:\.exe)?\s+-m\s+pytest(?:\s|$)", re.I),
    re.compile(r"^pytest(?:\.exe)?(?:\s|$)", re.I),
    re.compile(r"^git\s+(?:status|log|diff|branch|show|rev-parse)(?:\s|$)", re.I),
]


def allowed(cmd: str) -> bool:
    # 保守切分链式操作符；管道与重定向段不进白名单（前缀放行语义下，
    # pytest ... > file 视为 pytest 自检的一部分，等价于工匠本就有的文件写权限）
    segs = re.split(r"&&|\|\||;|&", cmd)
    segs = [s.strip() for s in segs if s.strip()]
    return bool(segs) and all(any(r.match(s) for r in ALLOW_RES) for s in segs)


def main() -> int:
    try:
        data = json.load(sys.stdin)
        cmd = str(data.get("command") or "")
    except Exception:
        return 2  # 输入不可读 = 拦（failClosed 语义兜底）
    ok = allowed(cmd)
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
           "decision": "allow" if ok else "deny",
           "command": cmd[:300]}
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 留痕失败不改变裁决
    if ok:
        json.dump({"permission": "allow"}, sys.stdout)
        return 0
    json.dump({
        "permission": "deny",
        "user_message": "门卫拒绝：白名单外命令（仅放行 pytest 自检与只读 git 查询）。"
                        "卡内确需其他命令时，在汇报中如实说明 BLOCKED 与原因，由大师裁决。",
    }, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
