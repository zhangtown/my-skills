#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deepseek_client.py — DeepSeek API 轻量客户端 (纯标准库)

只用 urllib，不依赖 requests/openai，Windows / Mac 直接可跑。
DeepSeek 提供 OpenAI 兼容接口。

配置 (环境变量)：
  DEEPSEEK_API_KEY   必填，你的 API Key
  DEEPSEEK_BASE_URL  可选，默认 https://api.deepseek.com
  DEEPSEEK_MODEL     可选，默认 deepseek-chat

用法：
  from deepseek_client import DeepSeekClient
  client = DeepSeekClient()
  text = client.chat([{"role":"user","content":"你好"}])
  obj  = client.chat_json([...])   # 强制返回 JSON 对象并解析
"""

import os
import json
import time
import urllib.request
import urllib.error


class DeepSeekError(RuntimeError):
    pass


def _fix_unescaped_quotes(text):
    """修复 JSON 字符串内部未转义的直引号。

    模型习惯用直引号（" "）强调术语/引用（如 "一张图"、"驻场+远程"），
    但这类引号若不转义会被解析器当成字符串提前结束，导致
    'Expecting , delimiter' 报错。

    做法：逐字符扫描，只在处于字符串内部时才处理；遇到 " 时，
    向后跳过空白看下一个非空白字符——如果是合法的 JSON 分隔符
    （, } ] :）或已到末尾，才认为这是真正的收尾引号；否则视为
    内容中的引号，转义成 \\" 后继续留在字符串内。
    """
    out = []
    in_str = False
    escape = False
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if not in_str:
            out.append(ch)
            if ch == '"':
                in_str = True
            i += 1
            continue
        if escape:
            out.append(ch)
            escape = False
            i += 1
            continue
        if ch == '\\':
            out.append(ch)
            escape = True
            i += 1
            continue
        if ch == '"':
            j = i + 1
            while j < n and text[j] in ' \t\r\n':
                j += 1
            nxt = text[j] if j < n else ''
            if nxt in (',', '}', ']', ':') or nxt == '':
                out.append(ch)
                in_str = False
            else:
                out.append('\\"')
            i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _fix_missing_closers(text):
    """修复缺失的收尾括号（模型偶尔漏写某层 } 导致后续括号错位）。

    逐字符扫描（跳过字符串内部内容），维护一个 { [ 的栈；遇到收尾符时
    若与栈顶不匹配，说明中间某层忘了收尾，先把缺的收尾符补上再继续；
    扫描结束后栈里剩下的层级，依次在末尾补齐。
    """
    out = []
    stack = []
    in_str = False
    escape = False
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch in '{[':
            stack.append(ch)
            out.append(ch)
            i += 1
            continue
        if ch in '}]':
            if stack and ch == ('}' if stack[-1] == '{' else ']'):
                stack.pop()
                out.append(ch)
            elif stack:
                # 缺了中间层的收尾符：先补齐，再落下当前这个收尾符
                while stack and ch != ('}' if stack[-1] == '{' else ']'):
                    out.append('}' if stack[-1] == '{' else ']')
                    stack.pop()
                if stack:
                    stack.pop()
                out.append(ch)
            else:
                out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    while stack:
        out.append('}' if stack[-1] == '{' else ']')
        stack.pop()
    return ''.join(out)


# ---- JSON 解析失败诊断 ----
# 写到当前工作目录（技能目录在很多环境下是只读的，绝不能往里写）。
# 可用环境变量 DEEPSEEK_DEBUG_DIR 覆盖。
_DEBUG_DIR = os.environ.get("DEEPSEEK_DEBUG_DIR") or os.path.join(os.getcwd(), "json_debug")


def _dump_json_error(raw_text, s, e, first_err, second_err, stage):
    """JSON 解析失败时保存原始内容+诊断信息到调试文件。
    诊断本身绝不能成为新的崩溃点：任何写文件异常都吞掉只打印。"""
    try:
        _dump_json_error_inner(raw_text, s, e, first_err, second_err, stage)
    except Exception as ex:
        print(f"[json_debug] 无法写诊断文件（{ex}），跳过。", flush=True)


def _dump_json_error_inner(raw_text, s, e, first_err, second_err, stage):
    os.makedirs(_DEBUG_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    # 原始内容全文
    raw_path = os.path.join(_DEBUG_DIR, f"json_raw_{ts}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)
    # 诊断报告
    diag_path = os.path.join(_DEBUG_DIR, f"json_diag_{ts}.txt")
    with open(diag_path, "w", encoding="utf-8") as f:
        f.write(f"=== JSON 解析失败诊断 ===\n")
        f.write(f"时间: {ts}\n")
        f.write(f"阶段: {stage}\n")
        f.write(f"原文长度: {len(raw_text)} 字符\n")
        f.write(f"提取范围: [{s}:{e}] ({e - s} 字符)\n")
        f.write(f"\n--- 首次解析异常 ---\n")
        f.write(f"{type(first_err).__name__}: {first_err}\n")
        if second_err:
            f.write(f"\n--- 兜底解析异常 ---\n")
            f.write(f"{type(second_err).__name__}: {second_err}\n")
        # 首尾各 500 字
        f.write(f"\n--- 原文前 500 字符 ---\n")
        f.write(raw_text[:500])
        f.write(f"\n\n--- 原文后 500 字符 ---\n")
        f.write(raw_text[-500:])
        # 异常位置附近上下文（取 first_err 的 pos）
        pos = getattr(first_err, "pos", None)
        if pos is not None and pos < len(raw_text):
            f.write(f"\n\n--- 异常位置附近 [pos-200:pos+200] ---\n")
            f.write(raw_text[max(0, pos - 200):min(len(raw_text), pos + 200)])
            f.write(f"\n\n--- 该位置 repr 值 ---\n")
            f.write(repr(raw_text[max(0, pos - 50):min(len(raw_text), pos + 50)]))
    print(f"[json_debug] JSON解析异常，已保存诊断信息到：{diag_path}", flush=True)


class DeepSeekClient:
    def __init__(self, api_key=None, base_url=None, model=None,
                 timeout=120, max_retries=3):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL")
                         or "https://api.deepseek.com").rstrip("/")
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_raw = None   # 最近一次 chat_json 的模型原始返回文本（供上层记录日志）
        if not self.api_key:
            raise DeepSeekError(
                "未设置 DEEPSEEK_API_KEY 环境变量。\n"
                "  Windows(PowerShell): $env:DEEPSEEK_API_KEY=\"sk-xxx\"\n"
                "  macOS/Linux:        export DEEPSEEK_API_KEY=sk-xxx")

    # ---------------- 底层请求 ----------------
    def _post(self, payload):
        payload = dict(payload)
        payload.setdefault("model", self.model)
        url = f"{self.base_url}/chat/completions"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                obj = json.loads(body)
                return obj["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                detail = ""
                try:
                    detail = e.read().decode("utf-8")[:500]
                except Exception:
                    pass
                last_err = DeepSeekError(f"HTTP {e.code}: {detail}")
                # 4xx (除 429) 不重试
                if 400 <= e.code < 500 and e.code != 429:
                    raise last_err
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as e:
                last_err = DeepSeekError(f"请求失败: {e}")
            if attempt < self.max_retries:
                time.sleep(2 * attempt)  # 退避
        raise last_err if last_err else DeepSeekError("未知错误")

    # ---------------- 对外接口 ----------------
    def chat(self, messages, temperature=0.6, max_tokens=4000, model=None):
        """返回纯文本。model 可按调用覆盖（规划用 v4-pro、写作用 v4-flash）。"""
        return self._post({
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        })

    def chat_json(self, messages, temperature=0.6, max_tokens=4000, model=None,
                  _allow_model_repair=True):
        """强制 JSON 对象输出并解析为 dict。失败抛 DeepSeekError。

        解析顺序：直接解析 → 截取 {..} → 启发式修复（引号/括号）→
        最后兜底：把原文回喂给模型让它自己修一次（_allow_model_repair 防递归）。"""
        text = self._post({
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        })
        self.last_raw = text   # 保存原始返回，供 generate.py 记录"大模型实际写了什么/多长"
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # 兜底1：截取首个 { ... }
            s, e_idx = text.find("{"), text.rfind("}")
            if not (s != -1 and e_idx != -1 and e_idx > s):
                _dump_json_error(text, s, 0, e, None, "首解析失败")
                raise DeepSeekError(
                    f"返回内容不是合法 JSON（未找到 JSON 边界）\n"
                    f"  原始解析: {e}\n  原始长度={len(text)}\n"
                    f"  详情见调试文件")
            candidate = text[s:e_idx + 1]
            last_err = e
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as e2:
                last_err = e2
            # 兜底2/3/4：常见的模型输出瑕疵——
            #   a) 正文里用直引号强调术语，破坏了字符串边界
            #   b) 漏写某层收尾括号（多为截断/疏漏）
            # 依次尝试单独修复、再尝试两者叠加修复
            for repaired in (
                _fix_unescaped_quotes(candidate),
                _fix_missing_closers(candidate),
                _fix_missing_closers(_fix_unescaped_quotes(candidate)),
            ):
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError as e3:
                    last_err = e3
            # 兜底5：启发式修不动的（如正文里嵌了 JSON 示例），让模型自己修一次。
            if _allow_model_repair:
                print(f"[json_repair] 自动修复失败（{last_err}），回喂模型修复一次…", flush=True)
                fix_msgs = [
                    {"role": "system", "content":
                        "你是 JSON 修复器。用户给你一段无法解析的 JSON 文本，"
                        "你逐字保留其内容含义，只修复语法问题（字符串内未转义的引号、"
                        "缺失/错位的括号、混入的非 JSON 文本），输出修复后的合法 JSON 对象。"
                        "不要增删内容，不要解释。"},
                    {"role": "user", "content":
                        f"解析错误：{last_err}\n\n待修复文本：\n{text}"},
                ]
                try:
                    return self.chat_json(fix_msgs, temperature=0.0,
                                          max_tokens=max_tokens, model=model,
                                          _allow_model_repair=False)
                except Exception as e4:
                    last_err = e4
            _dump_json_error(text, s, e_idx + 1, e, last_err, "fallback失败(含启发式修复+模型修复尝试)")
            raise DeepSeekError(
                f"返回内容不是合法 JSON（首解析+兜底+自动修复+模型修复均失败）\n"
                f"  首解析: {e}\n  最终尝试解析: {last_err}\n"
                f"  原始长度={len(text)}, 提取范围=[{s}:{e_idx+1}]\n"
                f"  详情见调试文件")


if __name__ == "__main__":
    # 简单连通性自测：python deepseek_client.py
    c = DeepSeekClient()
    print(c.chat([{"role": "user", "content": "用一句话介绍你自己。"}]))
