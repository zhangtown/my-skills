# 从 gap-now.png 里量：深色卡下边缘 / 背景缝 / 白卡上边缘
Add-Type -AssemblyName System.Drawing
$bmp = [System.Drawing.Image]::FromFile("$env:TEMP\gap-now.png")
$x = $bmp.Width - 18

$isDark  = { param($c) $c.R -lt 80 -and $c.G -lt 80 -and $c.B -lt 90 }
$isBg    = { param($c) ([Math]::Abs($c.R - 239) -le 4) -and ([Math]::Abs($c.G - 240) -le 4) -and ([Math]::Abs($c.B - 243) -le 4) }
$isWhite = { param($c) $c.R -ge 250 -and $c.G -ge 250 -and $c.B -ge 250 }

$heroBottom = -1; $gapStart = -1; $gapEnd = -1; $cardTop = -1
for ($y = 0; $y -lt $bmp.Height; $y++) {
  $c = $bmp.GetPixel($x, $y)
  if (-not (& $isWhite $c) -and (& $isDark $c)) { $heroBottom = $y }
  if ($heroBottom -ge 0 -and $gapStart -lt 0 -and $y -gt $heroBottom) {
    # 深色卡下边缘之后：先吃掉 1px 描边/圆角过渡，再看背景缝
    if (& $isBg $c) { $gapStart = $y }
  }
  if ($gapStart -ge 0 -and $gapEnd -lt 0 -and $y -gt $gapStart -and -not (& $isBg $c)) {
    $gapEnd = $y
    if (& $isWhite $c -or $c.R -ge 200) { $cardTop = $y }
  }
  if ($cardTop -ge 0) { break }
}

Write-Output ("扫描列 x=$x  (图 {0}x{1})" -f $bmp.Width, $bmp.Height)
Write-Output ("深色状态卡下边缘: y={0}" -f $heroBottom)
Write-Output ("背景缝:          y={0}..{1}  = {2}px" -f $gapStart, ($gapEnd - 1), ($gapEnd - $gapStart))
Write-Output ("配置白卡上边缘:  y={0}" -f $cardTop)

# 再打印所有「明显色变」的位置，便于交叉核对（每 0.5s 打印不出格）
Write-Output "---- 交界处颜色 ----"
foreach ($y in ($heroBottom - 3)..($cardTop + 3)) {
  if ($y -lt 0 -or $y -ge $bmp.Height) { continue }
  $c = $bmp.GetPixel($x, $y)
  $tag = ""
  if ($y -eq $heroBottom) { $tag = " <- 深色卡底" }
  if ($y -eq $gapStart)   { $tag = " <- 缝开始" }
  if ($y -eq $gapEnd)     { $tag = " <- 缝结束" }
  if ($y -eq $cardTop)    { $tag = " <- 白卡顶" }
  Write-Output ("y={0,4}  {1,3},{2,3},{3,3}{4}" -f $y, $c.R, $c.G, $c.B, $tag)
}
$bmp.Dispose()
