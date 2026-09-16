Add-Type @"
using System;using System.Runtime.InteropServices;using System.Text;
public class Wi {
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
 public delegate bool EnumProc(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
 [DllImport("user32.dll")] public static extern int GetWindowTextLengthW(IntPtr h);
 [DllImport("user32.dll")] public static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW")] public static extern IntPtr GetWindowLongPtr(IntPtr h, int i);
 [DllImport("user32.dll", EntryPoint="GetClassLongPtrW")] public static extern IntPtr GetClassLongPtr(IntPtr h, int i);
 public struct RECT { public int L,T,R,B; }
 public struct POINT { public int X,Y; }
}
"@
$p = Get-Process gui -ErrorAction SilentlyContinue | Select-Object -First 1
$mypid=[uint32]$p.Id
$h=[IntPtr]::Zero
$cb=[Wi+EnumProc]{
  param($w,$l)
  $q=0; [Wi]::GetWindowThreadProcessId($w,[ref]$q)|Out-Null
  if([uint32]$q -eq $mypid -and [Wi]::IsWindowVisible($w) -and ([Wi]::GetWindowTextLengthW($w) -gt 3)){
    $r=New-Object Wi+RECT; [Wi]::GetWindowRect($w,[ref]$r)|Out-Null
    if(($r.R-$r.L) -gt 300){ $script:h=$w; return $false }
  }
  return $true
}
[Wi]::EnumWindows($cb,[IntPtr]::Zero)|Out-Null
if($h -eq [IntPtr]::Zero){ Write-Output "no window"; exit 1 }
$wr=New-Object Wi+RECT; [Wi]::GetWindowRect($h,[ref]$wr)|Out-Null
$cr=New-Object Wi+RECT; [Wi]::GetClientRect($h,[ref]$cr)|Out-Null
$pt=New-Object Wi+POINT; $pt.X=0; $pt.Y=0; [Wi]::ClientToScreen($h,[ref]$pt)|Out-Null
$sb=New-Object System.Text.StringBuilder 256
[Wi]::GetClassNameW($h,$sb,256)|Out-Null
$style=[int64][Wi]::GetWindowLongPtr($h,-16)
$ex=[int64][Wi]::GetWindowLongPtr($h,-20)
$cs=[int64][Wi]::GetClassLongPtr($h,-26)
Write-Output ("hwnd={0} class={1}" -f $h,$sb.ToString())
Write-Output ("window rect = {0},{1} .. {2},{3}  ({4}x{5})" -f $wr.L,$wr.T,$wr.R,$wr.B,($wr.R-$wr.L),($wr.B-$wr.T))
Write-Output ("client rect = 0,0 .. {0},{1}  ({2}x{3})" -f $cr.R,$cr.B,$cr.R,$cr.B)
Write-Output ("client origin on screen = {0},{1}  => NC frame left={2} top={3} right={4} bottom={5}" -f $pt.X,$pt.Y,($pt.X-$wr.L),($pt.Y-$wr.T),($wr.R-($pt.X+$cr.R)),($wr.B-($pt.Y+$cr.B)))
Write-Output ("GWL_STYLE  = 0x{0:X8}  WS_POPUP={1} WS_THICKFRAME={2} WS_CAPTION={3} WS_BORDER={4} WS_SYSMENU={5}" -f $style, [bool]($style -band 0x80000000), [bool]($style -band 0x00040000), [bool]($style -band 0x00C00000), [bool]($style -band 0x00800000), [bool]($style -band 0x00080000))
Write-Output ("GWL_EXSTYLE= 0x{0:X8}  WS_EX_APPWINDOW={1} WS_EX_LAYERED={2}" -f $ex, [bool]($ex -band 0x00040000), [bool]($ex -band 0x00080000))
Write-Output ("GCL_STYLE  = 0x{0:X8}  CS_DROPSHADOW(0x20000)={1}" -f $cs, [bool]($cs -band 0x00020000))
