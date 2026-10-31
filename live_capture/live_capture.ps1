# Live in-game line capture: about every 30 seconds while NBA games are on.
# Saves only rows that changed, to live_capture\data\YYYY-MM-DD.csv next to this script.
# Keeps the computer awake while running. Stops by itself when every game of the night is final,
# or close the window to stop it any time.
# Works in Windows PowerShell 5.1 (built into Windows) and PowerShell 7.

param([int]$Seconds = 30, [string]$Date = "")

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# keep the computer from sleeping while this window is open
try {
    Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);' -ErrorAction Stop
    $keepAwake = { try { [void][Win32.Power]::SetThreadExecutionState([uint32]2147483649) } catch { } }   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
} catch { $keepAwake = { } }

# game night: before 6 AM still counts as the previous night
if ($Date -eq "") {
    $now = Get-Date
    if ($now.Hour -lt 6) { $now = $now.AddDays(-1) }
    $Date = $now.ToString("yyyy-MM-dd")
}
$books = @{ "15" = "Consensus"; "68" = "DraftKings"; "69" = "FanDuel"; "2988" = "Fanatics" }
$dataDir = Join-Path $PSScriptRoot "data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$out = Join-Path $dataDir "$Date.csv"
$url = "https://api.actionnetwork.com/web/v2/scoreboard/nba?bookIds=15,68,69,2988&date=" + $Date.Replace("-", "")
$outP = Join-Path $dataDir "periods_$Date.csv"
$pBooks = @{ "15" = "Consensus"; "30" = "Open"; "68" = "DraftKings"; "69" = "FanDuel"; "71" = "BetRivers"; "75" = "BetMGM"; "79" = "bet365"; "123" = "Caesars"; "2988" = "Fanatics" }
$periods = @("game", "firsthalf", "secondhalf", "firstquarter")
$last = @{}       # game|book -> last saved values
$lastP = @{}      # game|period|book -> last saved values
$errors = 0

function Pick($list, $side) {
    foreach ($o in @($list)) { if ($o -and $o.side -eq $side -and $o.is_live) { return $o } }
    return $null
}
function Val($o, $field) { if ($o) { return $o.$field } else { return $null } }

Write-Host "Live line capture for $Date. Saving to $out"
Write-Host "Checking every $Seconds seconds. Close this window to stop."

while ($true) {
    & $keepAwake
    try {
        $resp = Invoke-RestMethod -Uri $url -Headers @{ "User-Agent" = "Mozilla/5.0"; "Accept" = "application/json" } -TimeoutSec 20
        $errors = 0
    } catch {
        $errors++
        Write-Host ("{0:HH:mm:ss}  couldn't reach Action Network ({1}); trying again" -f (Get-Date), $_.Exception.Message)
        Start-Sleep -Seconds ([Math]::Min(120, $Seconds * $errors))
        continue
    }
    $games = @($resp.games)
    $live = @($games | Where-Object { $_.status -eq "inprogress" -or $_.status -eq "halftime" -or $_.real_status -eq "inprogress" })
    $finals = @("complete", "closed", "final")
    $notDone = @($games | Where-Object { ($finals -notcontains $_.status) -and ($finals -notcontains $_.real_status) })
    $rows = @()
    $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    foreach ($g in $live) {
        $abbr = @{}; foreach ($t in @($g.teams)) { $abbr[[string]$t.id] = $t.abbr }
        $hp = 0; $ap = 0
        foreach ($q in @($g.boxscore.linescore)) { if ($q.home_points) { $hp += $q.home_points }; if ($q.away_points) { $ap += $q.away_points } }
        foreach ($p in $g.markets.PSObject.Properties) {
            $ev = $p.Value.event
            if (-not $ev) { continue }
            $hs = Pick $ev.spread "home"; $as = Pick $ev.spread "away"
            $ov = Pick $ev.total "over"; $un = Pick $ev.total "under"
            $hm = Pick $ev.moneyline "home"; $am = Pick $ev.moneyline "away"
            if (-not ($hs -or $ov -or $hm)) { continue }
            $row = [ordered]@{
                seen_at_et = $stamp; an_game_id = $g.id; date = $Date
                away = $abbr[[string]$g.away_team_id]; home = $abbr[[string]$g.home_team_id]
                status = $g.status_display; period = $g.boxscore.period; clock = $g.boxscore.clock
                away_score = $ap; home_score = $hp; book = $books[$p.Name]
                home_spread = (Val $hs "value"); home_spread_odds = (Val $hs "odds"); away_spread_odds = (Val $as "odds")
                total = (Val $ov "value"); over_odds = (Val $ov "odds"); under_odds = (Val $un "odds")
                home_ml = (Val $hm "odds"); away_ml = (Val $am "odds")
            }
            $key = "$($g.id)|$($p.Name)"
            $sig = ($row.Keys | Where-Object { $_ -ne "seen_at_et" -and $_ -ne "status" -and $_ -ne "clock" } | ForEach-Object { [string]$row[$_] }) -join ","
            if ($last[$key] -ne $sig) { $last[$key] = $sig; $rows += [pscustomobject]$row }
        }
    }
    if ($rows.Count -gt 0) { $rows | Export-Csv -Path $out -Append -NoTypeInformation -Encoding UTF8 }

    # halves, 1st quarter and team totals at each book (raw values as posted; games not yet final)
    $prow = @()
    foreach ($per in $periods) {
        try {
            $pu = "https://api.actionnetwork.com/web/v1/scoreboard/nba?period=$per&bookIds=15,30,68,69,71,75,79,123,2988&date=" + $Date.Replace("-", "")
            $pr = Invoke-RestMethod -Uri $pu -Headers @{ "User-Agent" = "Mozilla/5.0"; "Accept" = "application/json" } -TimeoutSec 20
        } catch { Write-Host ("{0:HH:mm:ss}  couldn't get {1} lines this time" -f (Get-Date), $per); continue }
        foreach ($g in @($pr.games)) {
            if (@("scheduled", "inprogress", "halftime") -notcontains $g.status) { continue }
            $abbr = @{}; foreach ($t in @($g.teams)) { $abbr[[string]$t.id] = $t.abbr }
            $hp = 0; $ap = 0
            foreach ($q in @($g.boxscore.linescore)) { if ($q.home_points) { $hp += $q.home_points }; if ($q.away_points) { $ap += $q.away_points } }
            foreach ($o in @($g.odds)) {
                if (-not $o) { continue }
                $r = [ordered]@{
                    seen_at_et = $stamp; an_game_id = $g.id; date = $Date
                    away = $abbr[[string]$g.away_team_id]; home = $abbr[[string]$g.home_team_id]
                    status = $g.status; game_clock = $g.status_display; away_score = $ap; home_score = $hp
                    period = $per; book = $pBooks[[string]$o.book_id]
                    home_spread = $o.spread_home; home_spread_odds = $o.spread_home_line; away_spread_odds = $o.spread_away_line
                    total = $o.total; over_odds = $o.over; under_odds = $o.under; home_ml = $o.ml_home; away_ml = $o.ml_away
                    away_team_total = $o.away_total; away_tt_over_odds = $o.away_over; away_tt_under_odds = $o.away_under
                    home_team_total = $o.home_total; home_tt_over_odds = $o.home_over; home_tt_under_odds = $o.home_under
                }
                $key = "$($g.id)|$per|$($o.book_id)"
                $sig = ($r.Keys | Where-Object { @("seen_at_et", "game_clock", "away_score", "home_score") -notcontains $_ } | ForEach-Object { [string]$r[$_] }) -join ","
                if ($lastP[$key] -ne $sig) { $lastP[$key] = $sig; $prow += [pscustomobject]$r }
            }
        }
    }
    if ($prow.Count -gt 0) { $prow | Export-Csv -Path $outP -Append -NoTypeInformation -Encoding UTF8 }
    Write-Host ("{0:HH:mm:ss}  {1} games live, {2} live-line and {3} half/quarter/team-total changes saved" -f (Get-Date), $live.Count, $rows.Count, $prow.Count)
    if ($games.Count -gt 0 -and $notDone.Count -eq 0) { Write-Host "All games are final. Done for tonight."; break }
    $h = (Get-Date).Hour
    if ($live.Count -eq 0 -and $h -ge 3 -and $h -lt 12) { Write-Host "No games live and it's after 3 AM. Done for tonight."; break }
    if ($live.Count -eq 0) { Start-Sleep -Seconds 120 } else { Start-Sleep -Seconds $Seconds }
}
