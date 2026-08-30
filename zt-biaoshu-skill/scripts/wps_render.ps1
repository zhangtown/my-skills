param(
  [string]$InFile,
  [string]$OutPdf,
  [switch]$NoFields
)
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject KWPS.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
  $doc = $w.Documents.Open($InFile, $false, $true)  # ConfirmConversions=false, ReadOnly=true
  if (-not $NoFields) {
    try { $doc.Fields.Update() | Out-Null } catch { }
    try { for ($i = 1; $i -le $doc.TablesOfContents.Count; $i++) { $doc.TablesOfContents.Item($i).Update() } } catch { }
  }
  $pages = $doc.ComputeStatistics(2)  # wdStatisticPages
  Write-Output "PAGES=$pages"
  if ($OutPdf) {
    $doc.ExportAsFixedFormat($OutPdf, 17)
    Write-Output "PDF_OK"
  }
  $doc.Close($false)
} finally {
  $w.Quit()
}
