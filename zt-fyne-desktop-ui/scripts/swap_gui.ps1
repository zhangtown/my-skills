$dir = 'D:\ProgramData\projects\ZtRemoteNet\dist\RemoteNet-Portable'
Get-Process gui -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 900
$new = Join-Path $dir 'gui.new.exe'
$old = Join-Path $dir 'gui.exe'
if (-not (Test-Path $new)) { Write-Output "NO gui.new.exe"; exit 1 }
if (Test-Path $old) { Remove-Item $old -Force -ErrorAction SilentlyContinue }
Move-Item $new $old -Force
Start-Sleep -Milliseconds 300
Start-Process -FilePath $old -WorkingDirectory $dir
Start-Sleep -Seconds 3
$p = Get-Process gui -ErrorAction SilentlyContinue | Select-Object -First 1
if ($p) { Write-Output ("started pid={0} path={1}" -f $p.Id, $p.Path) } else { Write-Output "START FAILED" }
