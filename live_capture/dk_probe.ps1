# One-time probe (Nov 5, 2026): can THIS computer read DraftKings' own Connecticut feed, and does it list the games you can bet?
# GitHub's servers get "Access Denied" (403) from DraftKings; a home internet connection usually does not.
# Saves the raw replies to data\dk_probe\ and prints, per league, the games DraftKings lists with the total it shows.
$ErrorActionPreference = "Continue"
$dir = Join-Path $PSScriptRoot "data\dk_probe"; New-Item -ItemType Directory -Force -Path $dir | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$hdr = @{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
          "Accept" = "application/json"; "Origin" = "https://sportsbook.draftkings.com"; "Referer" = "https://sportsbook.draftkings.com/" }
$leagues = [ordered]@{ "NBA" = 42648; "NHL" = 42133; "NFL" = 88808 }
foreach ($site in @("dkusct", "dkusnj")) {          # Connecticut (your app) and New Jersey, to see whether lines differ by state
  foreach ($lg in $leagues.Keys) {
    $url = "https://sportsbook-nash.draftkings.com/api/sportscontent/$site/v1/leagues/$($leagues[$lg])"
    Write-Host ""; Write-Host "=== $lg ($site) ===" -ForegroundColor Cyan
    try {
      $r = Invoke-WebRequest -Uri $url -Headers $hdr -UseBasicParsing -TimeoutSec 30
      $file = Join-Path $dir "$stamp`_$site`_$lg.json"; [IO.File]::WriteAllText($file, $r.Content)
      Write-Host "HTTP $($r.StatusCode), $($r.Content.Length) bytes -> $file"
      try {
        $j = $r.Content | ConvertFrom-Json
        Write-Host ("Top-level keys: " + (($j.PSObject.Properties.Name) -join ", "))
        Write-Host ("events: " + @($j.events).Count + ", markets: " + @($j.markets).Count + ", selections: " + @($j.selections).Count)
        foreach ($e in @($j.events)) {
          $tm = @($j.markets | Where-Object { $_.eventId -eq $e.id -and $_.name -eq "Total" })
          $txt = "no full-game Total listed"
          if ($tm.Count -gt 0) {
            $sel = @($j.selections | Where-Object { $_.marketId -eq $tm[0].id })
            $txt = ($sel | ForEach-Object { "$($_.label) $($_.points) ($($_.displayOdds.american))" }) -join " | "
          }
          Write-Host ("  " + $e.name + "  [" + $e.startEventDate + "]  " + $txt)
        }
      } catch { Write-Host "Saved the reply but could not read its layout: $($_.Exception.Message)" -ForegroundColor Yellow }
    } catch {
      $code = $_.Exception.Response.StatusCode.value__
      Write-Host "FAILED: HTTP $code  $($_.Exception.Message)" -ForegroundColor Red
    }
  }
}
Write-Host ""; Write-Host "Done. Screenshot or copy this window and send it to Claude." -ForegroundColor Green
