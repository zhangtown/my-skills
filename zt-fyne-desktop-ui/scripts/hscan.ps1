Add-Type -AssemblyName System.Drawing
$bmp = [System.Drawing.Image]::FromFile("$env:TEMP\gap-now.png")
function HScan($y, $label) {
  $prev = ""; $runs = @(); $start = 0
  for ($x = 0; $x -lt $bmp.Width; $x++) {
    $c = $bmp.GetPixel($x, $y)
    $k = "{0},{1},{2}" -f $c.R, $c.G, $c.B
    if ($k -ne $prev) { if ($prev -ne "") { $runs += ("{0}..{1}({2}) {3}" -f $start, ($x-1), ($x-$start), $prev) }; $prev = $k; $start = $x }
  }
  $runs += ("{0}..{1}({2}) {3}" -f $start, ($bmp.Width-1), ($bmp.Width-$start), $prev)
  Write-Output "== $label (y=$y) =="
  ($runs | Select-Object -First 8) | ForEach-Object { Write-Output ("   " + $_) }
}
HScan 100 "深色状态卡"      # hero 中部
HScan 260 "配置白卡"        # 第一张白卡中部
$bmp.Dispose()
