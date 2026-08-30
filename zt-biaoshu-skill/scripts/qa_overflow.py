# -*- coding: utf-8 -*-
"""通过 Chrome DevTools Protocol 测量页面内容高度，检测溢出（单脚本自启自停）。
用法: python qa_overflow.py [工作目录]   （默认当前目录；页面位于 <工作目录>/mockgen/mockups）
"""
import asyncio, json, os, sys, urllib.request
import websockets

CHROME = os.environ.get("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
MOCKUPS = os.path.join(BASE, "mockgen", "mockups")
PORT = 9225

class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.counter = 0
    async def call(self, method, params=None, session=None):
        self.counter += 1
        mid = self.counter
        msg = {"id": mid, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        await self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(await self.ws.recv())
            if r.get("id") == mid:
                return r

async def main():
    proc = await asyncio.create_subprocess_exec(
        CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
        f"--remote-debugging-port={PORT}", "--user-data-dir=" + os.path.join(BASE, ".chrome-profile"),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        ver = None
        for _ in range(25):
            await asyncio.sleep(1)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2) as r:
                    ver = json.loads(r.read().decode())
                break
            except Exception:
                continue
        if not ver:
            print("chrome did not start"); return
        async with websockets.connect(ver["webSocketDebuggerUrl"]) as ws:
            cdp = CDP(ws)
            resp = await cdp.call("Target.getTargets")
            targets = [t for t in resp["result"]["targetInfos"] if t["type"] == "page"]
            tid = targets[0]["targetId"]
            att = await cdp.call("Target.attachToTarget", {"targetId": tid, "flatten": True})
            session = att["result"]["sessionId"]
            await cdp.call("Emulation.setDeviceMetricsOverride", {"width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False}, session)
            await cdp.call("Page.enable", None, session)
            issues = []
            for name in sorted(os.listdir(MOCKUPS)):
                if not name.endswith(".html"):
                    continue
                url = "file:///" + os.path.join(MOCKUPS, name).replace("\\", "/")
                await cdp.call("Page.navigate", {"url": url}, session)
                await asyncio.sleep(1.2)
                r = await cdp.call("Runtime.evaluate", {"expression": "JSON.stringify({docH: document.documentElement.scrollHeight, bodyW: document.body.scrollWidth})", "returnByValue": True}, session)
                val = json.loads(r["result"]["result"]["value"])
                flag = ""
                if val.get("docH", 0) > 1085 or val.get("bodyW", 0) > 1925:
                    flag = "  <<< OVERFLOW"
                    issues.append((name, val))
                print(f"{name}: docH={val.get('docH')} bodyW={val.get('bodyW')}{flag}")
            print("\nISSUES:", len(issues))
    finally:
        try: proc.terminate()
        except Exception: pass

asyncio.run(main())
