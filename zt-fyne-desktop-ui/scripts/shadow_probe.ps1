# 在纯白背景上量 gui.exe 窗口四周的投影：每条边向外 16px 的真实像素梯度
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$sig = @'
using System;
using System.Runtime.InteropServices;
public class S32 {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
'@
if (-not ('S32' -as [type])) { Add-Type -TypeDefinition $sig }

$p = Get-Process gui -ErrorAction SilentlyContinue | Sort-Object StartTime | Select-Object -Last 1
if (-not $p) { Write-Output "gui.exe 没在跑"; exit 1 }
$h = $p.MainWindowHandle
$r0 = New-Object 'S32+RECT'
[void][S32]::GetWindowRect($h, [ref]$r0)
Write-Output ("窗口原位 {0},{1} {2}x{3}" -f $r0.L, $r0.T, ($r0.R-$r0.L), ($r0.B-$r0.T))

$form = New-Object System.Windows.Forms.Form
$form.FormBorderStyle = 'None'
$form.BackColor = [System.Drawing.Color]::White
$form.StartPosition = 'Manual'
$form.Location = New-Object System.Drawing.Point(420, 60)
$form.Size = New-Object System.Drawing.Size(1100, 960)
$form.ShowInTaskbar = $false
$form.Show()
[System.Windows.Forms.Application]::DoEvents()
Start-Sleep -Milliseconds 400

[void][S32]::SetWindowPos($h, [IntPtr]::Zero, 700, 160, 0, 0, 0x0001 -bor 0x0004)
[void][S32]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 600

$r = New-Object 'S32+RECT'
[void][S32]::GetWindowRect($h, [ref]$r)
$w = $r.R - $r.L; $ht = $r.B - $r.T
$m = 16
$bmp = New-Object System.Drawing.Bitmap(($w + 2*$m), ($ht + 2*$m))
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen(($r.L - $m), ($r.T - $m), 0, 0, (New-Object System.Drawing.Size(($w + 2*$m), ($ht + 2*$m))))
$g.Dispose()
$out = "$env:TEMP\shadow-probe.png"
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output ("量测位置 {0},{1} {2}x{3}  截图 -> {4}" -f $r.L, $r.T, $w, $ht, $out)

$cx = [int]($w / 2); $cy = [int]($ht / 2)

function Row($label, $dir) {
  $s = @()
  for ($k = 1; $k -le $m; $k++) {
    switch ($dir) {
      'L' { $x = $m - $k;               $y = $m + $cy }
      'R' { $x = $m + $w + $k - 1;      $y = $m + $cy }
      'T' { $x = $m + $cx;              $y = $m - $k }
      'B' { $x = $m + $cx;              $y = $m + $ht + $k - 1 }
    }
    $c = $bmp.GetPixel([int]$x, [int]$y)
    $s += ("{0},{1},{2}" -f $c.R, $c.G, $c.B)
  }
  Write-Output ("{0} 1..16px 向外: {1}" -f $label, ($s -join "  "))
}

Write-Output "---- 窗外像素（255,255,255 = 纯背景无投影）----"
Row "左 " 'L'
Row "右 " 'R'
Row "上 " 'T'
Row "下 " 'B'

# 角上（右下角外侧，最能看出「有没有柔和阴影」）
Write-Output "---- 右下角外侧 3x3 采样点（间隔 4px）----"
for ($j = 1; $j -le 3; $j++) {
  $line = @()
  for ($i = 1; $i -le 3; $i++) {
    $c = $bmp.GetPixel(($m + $w + 4*$i), ($m + $ht + 4*$j))
    $line += ("+{0}/+{1}={2},{3},{4}" -f (4*$i), (4*$j), $c.R, $c.G, $c.B)
  }
  Write-Output ("   " + ($line -join "  "))
}

[void][S32]::SetWindowPos($h, [IntPtr]::Zero, $r0.L, $r0.T, 0, 0, 0x0001 -bor 0x0004)
$form.Close(); $form.Dispose()
$bmp.Dispose()
Write-Output "窗口已回原位，白底已关"
