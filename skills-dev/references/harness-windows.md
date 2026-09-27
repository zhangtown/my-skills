# 描述触发率评测：在 Windows 上跑通（含必须打的补丁）

用途：回答"这个技能的 description 到底能不能被触发"。做法是造一批查询（该触发/不该触发），
让 `claude -p` 真实跑一遍，统计触发率，再按留出集挑最优描述。

源头工具（本机）：`~/.pi/agent/skills/skill-creator/`（`scripts/run_loop.py`、`scripts/run_eval.py`、
`scripts/improve_description.py`、`assets/eval_review.html`）。**不要直接改源头**：复制一份到工作区
（如 `skill-creator-local/`）再打补丁，源头保持干净。

## 一、四个必须打的补丁

### 1. `claude` 是 `claude.CMD`，不能用裸名字启动

Windows 上 npm 装的 `claude` 实际是 `claude.CMD`，`subprocess.Popen(["claude", ...])` 会直接
`FileNotFoundError: [WinError 2] 系统找不到指定的文件。`；而 `.CMD` 也不能被 `CreateProcess` 直接执行，
必须经 `cmd.exe /c` 包一层：

```python
claude_exe = shutil.which("claude") or "claude"
cmd = [claude_exe, "-p", query, "--output-format", "stream-json",
       "--verbose", "--include-partial-messages"]
if model:
    cmd.extend(["--model", model])
if claude_exe.lower().endswith((".cmd", ".bat")):
    cmd = ["cmd.exe", "/c"] + cmd        # ← 这一行是关键
```

`scripts/improve_description.py` 里的 `_call_claude()` 同样要改（它也是裸 `["claude", ...]`），
并且别忘了 `import shutil`。

### 2. 管道不能用 `select`

`select.select([process.stdout], [], [], 1.0)` 在 Windows 上只接受 socket，读管道会抛
`OSError: [WinError 10038] 在一个非套接字上尝试了一个操作。`。改成后台线程读行 → 队列：

```python
_line_queue = _queue.Queue()

def _pump(stream, out):
    try:
        while True:
            line = stream.readline()
            if not line:
                break
            out.put(line)
    except Exception:
        pass
    finally:
        out.put(b"")          # 结束哨兵

threading.Thread(target=_pump, args=(process.stdout, _line_queue), daemon=True).start()

# 主循环里替换 select + os.read：
try:
    chunk = _line_queue.get(timeout=1.0)
except _queue.Empty:
    if process.poll() is not None:
        break
    continue
if not chunk:
    break
buffer += chunk.decode("utf-8", errors="replace")
```

### 3. 触发判定要认"原生技能"这一路

工具最初假设技能是通过 `<项目>/.claude/commands/<技能名>-skill-<id>.md` 这种**斜杠命令**暴露的，
于是判定写成"输入里出现命令文件名"；而且一旦第一个工具调用不是 `Skill`/`Read` 就直接判"未触发"。
新版 Claude Code 有原生技能：模型调用 `Skill` 工具时传的是**纯技能名**（`"skill": "fnos-app-dev"`），
并且可能先翻文件再调用技能。判定要改成：

```python
def _is_trigger(payload: str, tool_name: str, skill_name: str, clean_name: str) -> bool:
    if not payload:
        return False
    if tool_name == "Skill":
        return (f'"skill": "{skill_name}"' in payload
                or f'"skill":"{skill_name}"' in payload
                or clean_name in payload)
    # 读文件也算触发：skills/<技能名>/... 或命令文件名
    return (f"skills/{skill_name}" in payload
            or f"skills\\\\{skill_name}" in payload
            or clean_name in payload)
```

并且**不要把"第一个工具不是 Skill/Read"当成未触发**——扫完全部工具调用再下结论。
判定写错的表现很典型：日志里 `claude -p` 明明 exit=0、事件一堆，却清一色报"未触发"（假阴性）。

### 4. 技能得真的能被读到

harness 会在项目根下造命令文件，但模型也可能走"读技能目录"这条路（`~/.claude/skills/<名字>/SKILL.md`）。
所以跑评测前先确认技能已部署到对应 agent 的技能目录；新技能（还没部署）尤其容易因此被判成"未触发"。

## 二、怎么跑

评测集格式（20 条，10 正 10 负最稳）：

```json
[
  {"query": "把我在 NAS 上跑的那个 Go 服务做成应用中心能装的应用", "should_trigger": true},
  {"query": "帮我写个单元测试覆盖这个函数的分支", "should_trigger": false}
]
```

负例要**贴近**（共享关键词但其实是另一件事），明显无关的负例测不出东西。

启动（cwd 必须在含 `.claude/` 的目录里，harness 会往上找）：

```bash
cd <含 .claude 的工作目录>
PYTHONPATH="<本地 skill-creator-local 路径>" nohup python -m scripts.run_loop \
  --eval-set <评测集.json> \
  --skill-path <技能目录> \
  --model sonnet \
  --max-iterations 5 --verbose \
  --report <报告.html> --results-dir <结果目录> \
  > loop.log 2>&1 &
```

- 输出要及时看：`tail -f loop.log`。若出现一排 `Warning: query failed: [WinError 2]`，
  就是补丁 1/2 没打对。
- 前台 `cd A && nohup cmd > log &` 这种写法会把整条链后台化，**后续命令仍在原目录**，
  于是 `tail loop.log` 会找不到文件——用绝对路径看日志。
- 单条探针（改完判定后先验证再跑全量）：

```python
from scripts.run_eval import run_single_query
print(run_single_query(查询文本, "技能名", "描述文本", 120, "<项目根>", "sonnet"))
```

注意它的参数顺序是 `(query, skill_name, skill_description, timeout, project_root, model)`，
`timeout` 是**整数秒**（传错位置会得到 `TypeError: '<' not supported between instances of 'float' and 'str'`）。

## 三、失败症状速查

| 症状 | 原因 | 处理 |
|---|---|---|
| 一排 `WinError 2 系统找不到指定的文件` | `claude.CMD` 没经 `cmd.exe /c` | 补丁 1 |
| `WinError 10038 在一个非套接字上尝试了一个操作` | 用 `select` 读管道 | 补丁 2 |
| `TypeError: '<' not supported between 'float' and 'str'` | `timeout` 参数位置传错 | 见上"单条探针"签名 |
| 结果清一色"未触发"，但日志里 `claude` 退出码 0 | 判定逻辑只认命令文件 / 提前 return False | 补丁 3 |
| 结果飘忽、同一查询两次不同 | 查询太简单，模型自己就把活干了（不去查技能） | 换成多步、专业的查询 |
| 报告里找不到技能名 | 技能没部署到 agent 技能目录 | 补丁 4 |
