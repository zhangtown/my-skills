// shadowlab：在白底上逐个实测「无边框窗口 + 阴影」方案的像素效果。
// 每种方案起一个独立进程（-v N），跑完自己退出（带 30s 看门狗），最后 -sheet 拼对比图。
// 纯 stdlib + Win32（不用 x/sys，脱离仓库单独编译）。
package main

import (
	"flag"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

var (
	user32 = syscall.NewLazyDLL("user32.dll")
	gdi32  = syscall.NewLazyDLL("gdi32.dll")
	dwmapi = syscall.NewLazyDLL("dwmapi.dll")

	pRegisterClassExW    = user32.NewProc("RegisterClassExW")
	pCreateWindowExW     = user32.NewProc("CreateWindowExW")
	pDefWindowProcW      = user32.NewProc("DefWindowProcW")
	pPeekMessageW        = user32.NewProc("PeekMessageW")
	pTranslateMessage    = user32.NewProc("TranslateMessage")
	pDispatchMessageW    = user32.NewProc("DispatchMessageW")
	pSetWindowPos        = user32.NewProc("SetWindowPos")
	pGetWindowRect       = user32.NewProc("GetWindowRect")
	pGetClientRect       = user32.NewProc("GetClientRect")
	pGetDC               = user32.NewProc("GetDC")
	pReleaseDC           = user32.NewProc("ReleaseDC")
	pSetForegroundWindow = user32.NewProc("SetForegroundWindow")
	pBeginPaint          = user32.NewProc("BeginPaint")
	pEndPaint            = user32.NewProc("EndPaint")
	pFillRect            = user32.NewProc("FillRect")
	pSetProcessDPIAware  = user32.NewProc("SetProcessDPIAware")
	pGetSystemMetrics    = user32.NewProc("GetSystemMetrics")
	pLoadCursorW         = user32.NewProc("LoadCursorW")
	pSetBkMode           = gdi32.NewProc("SetBkMode")
	pSetTextColor        = gdi32.NewProc("SetTextColor")
	pDrawTextW           = user32.NewProc("DrawTextW")
	pCreateFontW         = gdi32.NewProc("CreateFontW")

	pCreateSolidBrush = gdi32.NewProc("CreateSolidBrush")
	pCreateCompatible = gdi32.NewProc("CreateCompatibleDC")
	pCreateDIBSection = gdi32.NewProc("CreateDIBSection")
	pBitBlt           = gdi32.NewProc("BitBlt")
	pDeleteDC         = gdi32.NewProc("DeleteDC")
	pSelectObject     = gdi32.NewProc("SelectObject")
	pGetStockObject   = gdi32.NewProc("GetStockObject")
	pRoundRect        = gdi32.NewProc("RoundRect")
	pDeleteObject     = gdi32.NewProc("DeleteObject")

	pDwmSetWindowAttribute        = dwmapi.NewProc("DwmSetWindowAttribute")
	pDwmExtendFrameIntoClientArea = dwmapi.NewProc("DwmExtendFrameIntoClientArea")
)

const (
	wsPopup        = 0x80000000
	wsThickFrame   = 0x00040000
	wsCaption      = 0x00C00000
	wsSysMenu      = 0x00080000
	wsMinimizeBox  = 0x00020000
	wsMaximizeBox  = 0x00010000
	wsClipSiblings = 0x04000000
	wsClipChildren = 0x02000000

	wsExAppWindow = 0x00040000

	csHRedraw    = 0x0002
	csVRedraw    = 0x0001
	csOwnDC      = 0x0020
	csDropshadow = 0x00020000

	wmPaint      = 0x000F
	wmNCCalcSize = 0x0083
	wmEraseBkgnd = 0x0014
	wmDestroy    = 0x0002

	swpNoSize     = 0x0001
	swpNoMove     = 0x0002
	swpNoZOrder   = 0x0004
	swpFrameChg   = 0x0020
	swpShowWindow = 0x0040
	swpHideWindow = 0x0080

	pmRemove = 0x0001

	dwmwaWindowCornerPreference = 33
	dwmwaBorderColor            = 34
	dwmwcpRound                 = 2
	// DWMWA_COLOR_NONE = 0xFFFFFFFE，按 int32 存
	dwmColorNone int32 = -2
)

type wndClassExW struct {
	CbSize        uint32
	Style         uint32
	LpfnWndProc   uintptr
	CbClsExtra    int32
	CbWndExtra    int32
	HInstance     uintptr
	HIcon         uintptr
	HCursor       uintptr
	HbrBackground uintptr
	LpszMenuName  *uint16
	LpszClassName *uint16
	HIconSm       uintptr
}

type rect struct{ Left, Top, Right, Bottom int32 }
type point struct{ X, Y int32 }

type msgT struct {
	Hwnd     uintptr
	Message  uint32
	WParam   uintptr
	LParam   uintptr
	Time     uint32
	Pt       point
	LPrivate uint32
}

type paintStruct struct {
	Hdc         uintptr
	Erase       int32
	RcPaint     rect
	Restore     int32
	IncUpdate   int32
	RgbReserved [32]byte
}

type bmiHeader struct {
	Size          uint32
	Width         int32
	Height        int32
	Planes        uint16
	BitCount      uint16
	Compression   uint32
	SizeImage     uint32
	XPelsPerMeter int32
	YPelsPerMeter int32
	ClrUsed       uint32
	ClrImportant  uint32
}

type bitmapInfo struct {
	Header bmiHeader
	Colors [3]uint32
}

type margins struct{ Left, Top, Right, Bottom int32 }

type variant struct {
	label      string // 图上的短标签
	desc       string // 报告里的完整说明
	style      uint32
	exStyle    uint32
	dropShadow bool // 类样式加 CS_DROPSHADOW（现状）
	fullClient bool // WM_NCCALCSIZE 返回 0：客户区铺满整个窗口
	round      bool // 圆角
	noBorder   bool // 去掉 1px 边框色
	dwmFrame   bool // DwmExtendFrameIntoClientArea(1,1,1,1)
}

var variants = []variant{
	{
		label: "A 现状 popup+dropshadow", desc: "WS_POPUP + 类样式 CS_DROPSHADOW（当前 gui.exe 的做法）",
		style: wsPopup | wsClipSiblings | wsClipChildren | wsSysMenu | wsMinimizeBox,
		exStyle: wsExAppWindow, dropShadow: true,
	},
	{
		label: "B popup+thickframe", desc: "WS_POPUP|WS_THICKFRAME + Win11 圆角 + 去掉边框色（Electron thickFrame 同款）",
		style:  wsPopup | wsThickFrame | wsClipSiblings | wsClipChildren | wsSysMenu | wsMinimizeBox | wsMaximizeBox,
		exStyle: wsExAppWindow, round: true, noBorder: true,
	},
	{
		label: "C B+客户区铺满", desc: "B + WM_NCCALCSIZE 返回 0（客户区铺满整个窗口矩形，帧只留给 DWM 画阴影）",
		style:  wsPopup | wsThickFrame | wsClipSiblings | wsClipChildren | wsSysMenu | wsMinimizeBox | wsMaximizeBox,
		exStyle: wsExAppWindow, fullClient: true, round: true, noBorder: true,
	},
	{
		label: "D 系统框+铺满", desc: "WS_OVERLAPPEDWINDOW（真·带标题栏的窗口）+ WM_NCCALCSIZE 铺满 + 圆角 + 去边框",
		style:  wsCaption | wsThickFrame | wsSysMenu | wsMinimizeBox | wsMaximizeBox | wsClipSiblings | wsClipChildren,
		exStyle: wsExAppWindow, fullClient: true, round: true, noBorder: true,
	},
	{
		label: "E popup+DwmExtendFrame", desc: "WS_POPUP + DwmExtendFrameIntoClientArea(1,1,1,1) + 圆角 + 去边框",
		style: wsPopup | wsClipSiblings | wsClipChildren | wsSysMenu | wsMinimizeBox,
		exStyle: wsExAppWindow, round: true, noBorder: true, dwmFrame: true,
	},
	{
		label: "F thickframe+DwmExtend", desc: "WS_POPUP|WS_THICKFRAME + DwmExtendFrameIntoClientArea(1,1,1,1) + 圆角 + 去边框",
		style:  wsPopup | wsThickFrame | wsClipSiblings | wsClipChildren | wsSysMenu | wsMinimizeBox | wsMaximizeBox,
		exStyle: wsExAppWindow, round: true, noBorder: true, dwmFrame: true,
	},
}

var (
	winW, winH = int32(420), int32(740)
	winX, winY = int32(620), int32(140)
	margin     = int32(26)

	bgBrush, heroBrush, whiteBrush uintptr
	curVariant                     int
	hwndVariant                    = map[uintptr]int{}
	outDir                         string
	logBuf                         strings.Builder
)

func logf(format string, a ...any) {
	fmt.Fprintf(&logBuf, format+"\n", a...)
	trace(strings.TrimRight(fmt.Sprintf(format, a...), "\n"))
}

func main() {
	vIdx := flag.Int("v", -1, "只跑第 N 种方案")
	sheet := flag.Bool("sheet", false, "把已生成的 vN.png 拼成对比图")
	hold := flag.Int("hold", 0, "只把窗口摆好并保持 N 秒（供外部截图），不自己做截图")
	flag.Parse()

	outDir = filepath.Join(os.Getenv("TEMP"), "shadowlab")
	_ = os.MkdirAll(outDir, 0o755)
	_ = os.Remove(filepath.Join(outDir, "trace.txt"))

	if *sheet {
		buildSheet()
		fmt.Println("对比图: " + filepath.Join(outDir, "compare.png"))
		return
	}
	if *vIdx < 0 || *vIdx >= len(variants) {
		panic("需要 -v N (0..5) 或 -sheet")
	}

	// 看门狗：某些窗口样式组合会让本进程卡在系统调用里，别让整个脚本跟着卡
	go func() {
		time.Sleep(90 * time.Second)
		logf("看门狗超时，强制退出")
		flushLog()
		os.Exit(3)
	}()

	defer func() {
		if r := recover(); r != nil {
			logf("panic: %v", r)
			flushLog()
			os.Exit(4)
		}
	}()

	pSetProcessDPIAware.Call()
	bgBrush, _, _ = pCreateSolidBrush.Call(0x00F3F0EF)   // #EFF0F3
	heroBrush, _, _ = pCreateSolidBrush.Call(0x00362B23) // #232B36
	whiteBrush, _, _ = pCreateSolidBrush.Call(0x00FFFFFF)

	// 白底：全屏无边框窗口，垫在最底下
	white, _, _ := pCreateSolidBrush.Call(0x00FFFFFF)
	registerClass("shadowlabBackdrop", csHRedraw|csVRedraw, white, backdropProc)
	sw, _, _ := pGetSystemMetrics.Call(0)
	sh, _, _ := pGetSystemMetrics.Call(1)
	backdrop := createWindow("shadowlabBackdrop", wsPopup, 0, 0, 0, int32(sw), int32(sh))
	pSetWindowPos.Call(backdrop, 0, 0, 0, 0, 0, swpShowWindow|swpNoZOrder|swpNoMove|swpNoSize)
	pump(300)

	registerClass("shadowlabDrop", csHRedraw|csVRedraw|csOwnDC|csDropshadow, white, wndProc)
	registerClass("shadowlabPlain", csHRedraw|csVRedraw|csOwnDC, white, wndProc)

	v := variants[*vIdx]
	cls := "shadowlabPlain"
	if v.dropShadow {
		cls = "shadowlabDrop"
	}
	curVariant = *vIdx
	h := createWindow(cls, v.style, v.exStyle, 50, 50, winW, winH)
	hwndVariant[h] = *vIdx

	logf("[%d] %s", *vIdx, v.desc)
	trace("-> SetWindowPos(show)")
	pSetWindowPos.Call(h, 0, uintptr(winX), uintptr(winY), uintptr(winW), uintptr(winH), swpShowWindow|swpNoZOrder)
	trace("-> SetForegroundWindow")
	pSetForegroundWindow.Call(h)
	trace("-> pump 900")
	pump(900)
	trace("-> pump done")

	applyDwm(h, v)
	trace("-> applyDwm done")

	if *hold > 0 {
		var hr rect
		pGetWindowRect.Call(h, uintptr(unsafe.Pointer(&hr)))
		_ = os.WriteFile(filepath.Join(outDir, "rect.txt"),
			[]byte(fmt.Sprintf("%d %d %d %d\n", hr.Left, hr.Top, hr.Right-hr.Left, hr.Bottom-hr.Top)), 0o644)
		logf("    hold %ds, rect=(%d,%d) %dx%d", *hold, hr.Left, hr.Top, hr.Right-hr.Left, hr.Bottom-hr.Top)
		flushLog()
		pump(*hold * 1000)
		os.Exit(0)
	}

	var wr rect
	trace("-> capture start")
	pGetWindowRect.Call(h, uintptr(unsafe.Pointer(&wr)))
	img := capture(wr.Left-margin, wr.Top-margin, (wr.Right-wr.Left)+2*margin, (wr.Bottom-wr.Top)+2*margin)
	trace("-> capture done")
	savePNG(filepath.Join(outDir, fmt.Sprintf("v%d.png", *vIdx)), img)
	trace("-> saved png")
	analyze(v, h, wr, img)
	trace("-> analyze done")

	flushLog()
	os.Exit(0)
}

func flushLog() {
	_ = os.WriteFile(filepath.Join(outDir, fmt.Sprintf("report-v%d.txt", curVariant)), []byte(logBuf.String()), 0o644)
}

func applyDwm(h uintptr, v variant) {
	if v.round {
		val := int32(dwmwcpRound)
		r, _, err := pDwmSetWindowAttribute.Call(h, dwmwaWindowCornerPreference, uintptr(unsafe.Pointer(&val)), 4)
		logf("    DWM 圆角 -> ret=%d err=%v", r, err)
	}
	if v.noBorder {
		val := int32(dwmColorNone)
		r, _, err := pDwmSetWindowAttribute.Call(h, dwmwaBorderColor, uintptr(unsafe.Pointer(&val)), 4)
		logf("    DWM 去边框色 -> ret=%d err=%v", r, err)
	}
	if v.dwmFrame {
		m := margins{1, 1, 1, 1}
		r, _, err := pDwmExtendFrameIntoClientArea.Call(h, uintptr(unsafe.Pointer(&m)))
		logf("    DWM ExtendFrame(1,1,1,1) -> ret=%d err=%v", r, err)
	}
	if v.round || v.noBorder || v.dwmFrame {
		trace("    applyDwm: SetWindowPos(FRAMECHANGED) 前")
		pSetWindowPos.Call(h, 0, 0, 0, 0, 0, swpNoSize|swpNoMove|swpNoZOrder|swpFrameChg)
		trace("    applyDwm: SetWindowPos 后，pump(250) 前")
		pump(250)
		trace("    applyDwm: pump(250) 后")
	}
}

func analyze(v variant, h uintptr, wr rect, img *image.RGBA) {
	var cr rect
	pGetClientRect.Call(h, uintptr(unsafe.Pointer(&cr)))
	logf("    窗口矩形 (%d,%d)-(%d,%d) %dx%d | 客户区 %dx%d | 客户区相对窗口偏移 (%d,%d)",
		wr.Left, wr.Top, wr.Right, wr.Bottom, wr.Right-wr.Left, wr.Bottom-wr.Top,
		cr.Right-cr.Left, cr.Bottom-cr.Top, cr.Left, cr.Top)

	w := int(wr.Right - wr.Left)
	hh := int(wr.Bottom - wr.Top)
	midY := int(margin) + hh/2
	midX := int(margin) + w/2
	rmax := int(margin)

	type edge struct {
		name   string
		x, y   int
		dx, dy int
	}
	edges := []edge{
		{"左", int(margin) - 1, midY, -1, 0},
		{"右", int(margin) + w, midY, 1, 0},
		{"上", midX, int(margin) - 1, 0, -1},
		{"下", midX, int(margin) + hh, 0, 1},
	}
	for _, e := range edges {
		vals := make([]int, 0, rmax)
		txt := make([]string, 0, rmax)
		for k := 1; k <= rmax; k++ {
			c := img.RGBAAt(e.x+e.dx*k, e.y+e.dy*k)
			l := int(lum(c))
			vals = append(vals, l)
			txt = append(txt, fmt.Sprintf("%d", l))
		}
		logf("    %s 向外 1..%dpx: %s", e.name, rmax, strings.Join(txt, " "))
		logf("       → 首像素 %d | 阴影跨度 %dpx | 最深 %d", vals[0], spread(vals), deepest(vals))
	}

	diag := func(name string, x0, y0, dx, dy int) {
		txt := make([]string, 0, 12)
		for k := 1; k <= 12; k++ {
			c := img.RGBAAt(x0+dx*k, y0+dy*k)
			txt = append(txt, fmt.Sprintf("%d", lum(c)))
		}
		logf("    %s 斜向外 1..12px: %s", name, strings.Join(txt, " "))
	}
	diag("左上角", int(margin), int(margin), -1, -1)
	diag("右下角", int(margin)+w, int(margin)+hh, 1, 1)
	logf("")
}

func lum(c color.RGBA) int { return (299*int(c.R) + 587*int(c.G) + 114*int(c.B)) / 1000 }

func spread(vals []int) int {
	n := 0
	for _, v := range vals {
		if v < 253 {
			n++
		}
	}
	return n
}

func deepest(vals []int) int {
	d := 255
	for _, v := range vals {
		if v < d {
			d = v
		}
	}
	return d
}

func registerClass(name string, style uint32, bg uintptr, wndproc func(h uintptr, m uint32, w, l uintptr) uintptr) {
	cn, _ := syscall.UTF16PtrFromString(name)
	wc := wndClassExW{
		Style:         style,
		LpfnWndProc:   syscall.NewCallback(wndproc),
		HbrBackground: bg,
		LpszClassName: cn,
	}
	wc.CbSize = uint32(unsafe.Sizeof(wc))
	hc, _, _ := pLoadCursorW.Call(0, 32512) // IDC_ARROW
	wc.HCursor = hc
	if r, _, err := pRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc))); r == 0 {
		panic("RegisterClassEx failed: " + err.Error())
	}
}

func createWindow(class string, style, ex uint32, x, y, w, h int32) uintptr {
	cn, _ := syscall.UTF16PtrFromString(class)
	title, _ := syscall.UTF16PtrFromString("shadowlab")
	hw, _, err := pCreateWindowExW.Call(uintptr(ex), uintptr(unsafe.Pointer(cn)), uintptr(unsafe.Pointer(title)),
		uintptr(style), uintptr(x), uintptr(y), uintptr(w), uintptr(h), 0, 0, 0, 0)
	if hw == 0 {
		panic("CreateWindowEx failed: " + err.Error())
	}
	return hw
}

func pump(ms int) {
	deadline := time.Now().Add(time.Duration(ms) * time.Millisecond)
	var m msgT
	for time.Now().Before(deadline) {
		n := 0
		for n < 64 { // 每轮最多抽 64 条，防止持续刷新的窗口把循环卡死
			r, _, _ := pPeekMessageW.Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0, pmRemove)
			if r == 0 {
				break
			}
			pTranslateMessage.Call(uintptr(unsafe.Pointer(&m)))
			pDispatchMessageW.Call(uintptr(unsafe.Pointer(&m)))
			n++
		}
		time.Sleep(6 * time.Millisecond)
	}
}

func trace(line string) {
	f, err := os.OpenFile(filepath.Join(outDir, "trace.txt"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return
	}
	fmt.Fprintln(f, line)
	f.Close()
}

// backdropProc 白底窗口：什么都不画，靠类背景刷保持纯白
func backdropProc(h uintptr, m uint32, w, l uintptr) uintptr {
	r, _, _ := pDefWindowProcW.Call(h, uintptr(m), w, l)
	return r
}

func wndProc(h uintptr, m uint32, w, l uintptr) uintptr {
	if m != wmPaint {
		trace(fmt.Sprintf("    wndProc msg 0x%04X w=%d l=%d", m, w, l))
	}
	switch m {
	case wmNCCalcSize:
		if idx, ok := hwndVariant[h]; ok && w != 0 && variants[idx].fullClient {
			return 0
		}
	case wmPaint:
		paint(h)
		return 0
	case wmEraseBkgnd:
		return 1
	case wmDestroy:
		return 0
	}
	r, _, _ := pDefWindowProcW.Call(h, uintptr(m), w, l)
	return r
}

func paint(h uintptr) {
	var ps paintStruct
	hdc, _, _ := pBeginPaint.Call(h, uintptr(unsafe.Pointer(&ps)))
	var cr rect
	pGetClientRect.Call(h, uintptr(unsafe.Pointer(&cr)))
	w, hh := cr.Right-cr.Left, cr.Bottom-cr.Top

	r := rect{0, 0, w, hh}
	pFillRect.Call(hdc, uintptr(unsafe.Pointer(&r)), bgBrush)
	hero := rect{0, 0, w, 150}
	pFillRect.Call(hdc, uintptr(unsafe.Pointer(&hero)), heroBrush)

	nullPen, _, _ := pGetStockObject.Call(8) // NULL_PEN
	oldPen, _, _ := pSelectObject.Call(hdc, nullPen)
	oldBrush, _, _ := pSelectObject.Call(hdc, whiteBrush)
	pRoundRect.Call(hdc, uintptr(10), uintptr(162), uintptr(int(w)-10), uintptr(300), 16, 16)
	pRoundRect.Call(hdc, uintptr(10), uintptr(312), uintptr(int(w)-10), uintptr(430), 16, 16)
	pSelectObject.Call(hdc, oldPen)
	pSelectObject.Call(hdc, oldBrush)

	pEndPaint.Call(h, uintptr(unsafe.Pointer(&ps)))
}

func capture(x, y, w, h int32) *image.RGBA {
	srcDC, _, _ := pGetDC.Call(0)
	defer pReleaseDC.Call(0, srcDC)
	memDC, _, _ := pCreateCompatible.Call(srcDC)
	defer pDeleteDC.Call(memDC)

	bi := bitmapInfo{}
	bi.Header.Size = uint32(unsafe.Sizeof(bmiHeader{}))
	bi.Header.Width = w
	bi.Header.Height = -h // 自顶向下
	bi.Header.Planes = 1
	bi.Header.BitCount = 32
	var bits unsafe.Pointer
	hbmp, _, _ := pCreateDIBSection.Call(memDC, uintptr(unsafe.Pointer(&bi)), 0, uintptr(unsafe.Pointer(&bits)), 0, 0)
	old, _, _ := pSelectObject.Call(memDC, hbmp)
	pBitBlt.Call(memDC, 0, 0, uintptr(w), uintptr(h), srcDC, uintptr(x), uintptr(y), 0x00CC0020|0x40000000)

	img := image.NewRGBA(image.Rect(0, 0, int(w), int(h)))
	pix := unsafe.Slice((*byte)(bits), int(w)*int(h)*4)
	for i := 0; i < int(w)*int(h); i++ {
		img.Pix[i*4+0] = pix[i*4+2]
		img.Pix[i*4+1] = pix[i*4+1]
		img.Pix[i*4+2] = pix[i*4+0]
		img.Pix[i*4+3] = 255
	}
	pSelectObject.Call(memDC, old)
	pDeleteObject.Call(hbmp)
	return img
}

func savePNG(path string, img image.Image) {
	f, err := os.Create(path)
	if err != nil {
		panic(err)
	}
	defer f.Close()
	_ = png.Encode(f, img)
}

// ---------- 对比图 ----------

func buildSheet() {
	caps := make([]*image.RGBA, len(variants))
	for i := range variants {
		f, err := os.Open(filepath.Join(outDir, fmt.Sprintf("v%d.png", i)))
		if err != nil {
			panic(err)
		}
		im, err := png.Decode(f)
		f.Close()
		if err != nil {
			panic(err)
		}
		rgba := image.NewRGBA(im.Bounds())
		for y := im.Bounds().Min.Y; y < im.Bounds().Max.Y; y++ {
			for x := im.Bounds().Min.X; x < im.Bounds().Max.X; x++ {
				rgba.Set(x, y, im.At(x, y))
			}
		}
		caps[i] = rgba
	}

	zoomTL, zoomBR, region := 4, 4, 48
	srcW := int(winW + 2*margin)
	srcH := int(winH + 2*margin)
	halfW, halfH := srcW/2, srcH/2

	colW := srcW
	row1H := halfH
	row2H := region * zoomTL
	row3H := region * zoomBR
	headH, labelH := 30, 22
	sheetW := colW*len(caps) + (len(caps)-1)*14
	sheetH := headH + row1H + row2H + row3H + labelH*3 + 40

	sheet := image.NewRGBA(image.Rect(0, 0, sheetW, sheetH))
	fill(sheet, color.RGBA{248, 248, 248, 255})

	x := 0
	for _, img := range caps {
		scaleDown(sheet, x, headH, img, srcW, srcH, halfW, halfH)
		scaleUp(sheet, x, headH+row1H+labelH+8, img, 0, 0, region, region, zoomTL)
		scaleUp(sheet, x, headH+row1H+row2H+labelH*2+16, img, srcW-region, srcH-region, region, region, zoomBR)
		x += colW + 14
	}

	// 文字交给 GDI（Go 标准库没有字体）
	hdc, bits := dibDC(sheet)
	font, _, _ := pCreateFontW.Call(17, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 0, 0, uintptr(unsafe.Pointer(utf16p("Microsoft YaHei"))))
	oldFont, _, _ := pSelectObject.Call(hdc, font)
	pSetBkMode.Call(hdc, 1)
	pSetTextColor.Call(hdc, 0x00303030)

	x = 0
	for i, v := range variants {
		drawLabel(hdc, fmt.Sprintf("%d  %s", i, v.label), x+4, 5, colW)
		drawLabel(hdc, "整窗（缩小 50%）", x+4, headH-20, colW)
		drawLabel(hdc, "左上角 4x", x+4, headH+row1H+labelH-14, colW)
		drawLabel(hdc, "右下角 4x", x+4, headH+row1H+row2H+labelH*2+6, colW)
		_ = i
	}
	pSelectObject.Call(hdc, oldFont)
	pDeleteObject.Call(font)
	copyBack(sheet, bits)
	pDeleteDC.Call(hdc)
	savePNG(filepath.Join(outDir, "compare.png"), sheet)

	// 单出一张左上角 1x 拼图，方便直接看
	stripW := region*2*2*len(caps) + 10*(len(caps)-1)
	stripH := region * 2
	strip := image.NewRGBA(image.Rect(0, 0, stripW, stripH))
	fill(strip, color.RGBA{255, 255, 255, 255})
	for i, img := range caps {
		scaleUp(strip, i*(region*2+10), 0, img, 0, 0, region, region, 2)
	}
	savePNG(filepath.Join(outDir, "corners.png"), strip)
}

func drawLabel(hdc uintptr, s string, x, y, maxW int) {
	txt := utf16p(s)
	r := rect{int32(x), int32(y), int32(x + maxW), int32(y + 20)}
	pDrawTextW.Call(hdc, uintptr(unsafe.Pointer(txt)), ^uintptr(0), uintptr(unsafe.Pointer(&r)), 0x00000020)
}

func fill(img *image.RGBA, c color.RGBA) {
	for y := 0; y < img.Rect.Dy(); y++ {
		for x := 0; x < img.Rect.Dx(); x++ {
			img.SetRGBA(x, y, c)
		}
	}
}

func scaleDown(dst *image.RGBA, dx, dy int, src *image.RGBA, sw, sh, tw, th int) {
	for y := 0; y < th; y++ {
		for x := 0; x < tw; x++ {
			dst.SetRGBA(dx+x, dy+y, src.RGBAAt(x*sw/tw, y*sh/th))
		}
	}
}

func scaleUp(dst *image.RGBA, dx, dy int, src *image.RGBA, sx, sy, w, h, z int) {
	for y := 0; y < h*z; y++ {
		for x := 0; x < w*z; x++ {
			dst.SetRGBA(dx+x, dy+y, src.RGBAAt(sx+x/z, sy+y/z))
		}
	}
}

// dibDC 把 Go 图像送进 DIB 内存 DC 供 GDI 画字；copyBack 把结果抄回来
func dibDC(img *image.RGBA) (uintptr, unsafe.Pointer) {
	w, h := img.Rect.Dx(), img.Rect.Dy()
	srcDC, _, _ := pGetDC.Call(0)
	defer pReleaseDC.Call(0, srcDC)
	memDC, _, _ := pCreateCompatible.Call(srcDC)
	bi := bitmapInfo{}
	bi.Header.Size = uint32(unsafe.Sizeof(bmiHeader{}))
	bi.Header.Width = int32(w)
	bi.Header.Height = -int32(h)
	bi.Header.Planes = 1
	bi.Header.BitCount = 32
	var bits unsafe.Pointer
	hbmp, _, _ := pCreateDIBSection.Call(memDC, uintptr(unsafe.Pointer(&bi)), 0, uintptr(unsafe.Pointer(&bits)), 0, 0)
	pSelectObject.Call(memDC, hbmp)
	pix := unsafe.Slice((*byte)(bits), w*h*4)
	for i := 0; i < w*h; i++ {
		pix[i*4+0] = img.Pix[i*4+2]
		pix[i*4+1] = img.Pix[i*4+1]
		pix[i*4+2] = img.Pix[i*4+0]
		pix[i*4+3] = 255
	}
	return memDC, bits
}

func copyBack(img *image.RGBA, bits unsafe.Pointer) {
	w, h := img.Rect.Dx(), img.Rect.Dy()
	pix := unsafe.Slice((*byte)(bits), w*h*4)
	for i := 0; i < w*h; i++ {
		img.Pix[i*4+0] = pix[i*4+2]
		img.Pix[i*4+1] = pix[i*4+1]
		img.Pix[i*4+2] = pix[i*4+0]
		img.Pix[i*4+3] = 255
	}
}

func utf16p(s string) *uint16 {
	p, err := syscall.UTF16PtrFromString(s)
	if err != nil {
		panic(err)
	}
	return p
}
