param([int]$X, [int]$Y, [int]$W, [int]$H, [string]$Out, [string]$Mode = "dotnet")
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class CapGDI {
  [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr h);
  [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr dc);
  [DllImport("gdi32.dll")] public static extern bool BitBlt(IntPtr d, int x, int y, int w, int h, IntPtr s, int sx, int sy, int rop);
}
'@
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
if ($Mode -eq "gdi") {
  $hdc = $g.GetHdc()
  $src = [CapGDI]::GetDC([IntPtr]::Zero)
  [void][CapGDI]::BitBlt($hdc, 0, 0, $W, $H, $src, $X, $Y, 0x00CC0020)
  [void][CapGDI]::ReleaseDC([IntPtr]::Zero, $src)
  $g.ReleaseHdc($hdc)
} else {
  $g.CopyFromScreen($X, $Y, 0, 0, (New-Object System.Drawing.Size($W, $H)))
}
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "$Mode -> $Out"
