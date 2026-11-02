# NBA tracking and hustle stats from stats.nba.com, once a day (the NBA blocks cloud servers, so this runs on the laptop).
# Saves the raw replies to live_capture\data\tracking\YYYY-MM-DD\ (the date the download ran):
#   - season-to-date tables for every team and player: speed and distance, touches, passing, drives, catch-and-shoot,
#     pull-ups, paint/post/elbow touches, rebounding chances, defense at the rim, shots by closest-defender distance,
#     hustle stats (deflections, contested shots, screen assists, loose balls, box-outs)
#   - per-game tracking and hustle box scores for yesterday's games (each player's speed, distance, touches, passes,
#     contested shots...)
# Claude copies these into the GitHub repo (research/nba_tracking/) in each session.
# Run by hand: double-click Get_NBA_Tracking.bat. Scheduled daily by install_nightly_task.ps1.
# Works in Windows PowerShell 5.1 and PowerShell 7.

param([string]$Season = "2026-27", [string]$GameDate = "")

$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Add-Type -AssemblyName System.Net.Http
$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromSeconds(60)
$h = $client.DefaultRequestHeaders
[void]$h.TryAddWithoutValidation("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36")
[void]$h.TryAddWithoutValidation("Referer", "https://www.nba.com/")
[void]$h.TryAddWithoutValidation("Origin", "https://www.nba.com")
[void]$h.TryAddWithoutValidation("Accept", "application/json, text/plain, */*")
[void]$h.TryAddWithoutValidation("x-nba-stats-origin", "stats")
[void]$h.TryAddWithoutValidation("x-nba-stats-token", "true")

$today = Get-Date
if ($GameDate -eq "") { $GameDate = $today.AddDays(-1).ToString("yyyy-MM-dd") }
$outDir = Join-Path (Join-Path (Join-Path $PSScriptRoot "data") "tracking") $today.ToString("yyyy-MM-dd")
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$log = Join-Path $outDir "_log.txt"
$base = "https://stats.nba.com/stats/"
$ok = 0; $bad = 0

function Save($name, $endpoint, $query) {
    $url = $base + $endpoint + "?" + $query
    for ($i = 1; $i -le 3; $i++) {
        try {
            $r = $client.GetAsync($url).GetAwaiter().GetResult()
            $body = $r.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            if ($r.IsSuccessStatusCode -and $body.Length -gt 50) {
                [IO.File]::WriteAllText((Join-Path $outDir "$name.json"), $body)
                Add-Content $log "OK   $name ($($body.Length) bytes)"
                $script:ok++; Start-Sleep -Milliseconds 1500; return $body
            }
            Add-Content $log "TRY $i $name : HTTP $([int]$r.StatusCode)"
        } catch { Add-Content $log "TRY $i $name : $($_.Exception.Message)" }
        Start-Sleep -Seconds (5 * $i)
    }
    Add-Content $log "FAIL $name : $url"; $script:bad++; return $null
}

Add-Content $log "=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') season $Season, games of $GameDate"
$common = "LeagueID=00&Season=$Season&SeasonType=Regular+Season&PerMode=PerGame&LastNGames=0&Month=0&OpponentTeamID=0&PORound=0&Period=0" +
          "&DateFrom=&DateTo=&GameScope=&Location=&Outcome=&PlayerExperience=&PlayerPosition=&SeasonSegment=&StarterBench=&VsConference=&VsDivision=" +
          "&Conference=&Division=&TeamID=0&College=&Country=&DraftPick=&DraftYear=&Height=&Weight=&ISTRound="

# season-to-date tracking tables (team and player)
$measures = @("SpeedDistance", "Touches", "Passing", "Drives", "CatchShoot", "PullUpShot", "Possessions", "Rebounding", "Defense",
              "ElbowTouch", "PostTouch", "PaintTouch", "Efficiency")
foreach ($who in @("Team", "Player")) {
    foreach ($m in $measures) { [void](Save "pt_$($who.ToLower())_$m" "leaguedashptstats" "$common&PlayerOrTeam=$who&PtMeasureType=$m") }
}
# shots by closest defender distance (team)
$ranges = @{ "very_tight" = "0-2+Feet+-+Very+Tight"; "tight" = "2-4+Feet+-+Tight"; "open" = "4-6+Feet+-+Open"; "wide_open" = "6%2B+Feet+-+Wide+Open" }
foreach ($k in $ranges.Keys) {
    [void](Save "team_shots_def_$k" "leaguedashteamptshot" "$common&CloseDefDistRange=$($ranges[$k])&ShotClockRange=&DribbleRange=&TouchTimeRange=&GeneralRange=&ShotDistRange=")
    [void](Save "opp_shots_def_$k" "leaguedashoppptshot" "$common&CloseDefDistRange=$($ranges[$k])&ShotClockRange=&DribbleRange=&TouchTimeRange=&GeneralRange=&ShotDistRange=")
}
# team defense by shot area, and hustle
foreach ($c in @("Overall", "3+Pointers", "2+Pointers", "Less+Than+6Ft", "Less+Than+10Ft", "Greater+Than+15Ft")) {
    [void](Save ("team_defend_" + $c.Replace("+", "_")) "leaguedashptteamdefend" "$common&DefenseCategory=$c")
}
[void](Save "hustle_team" "leaguehustlestatsteam" $common)
[void](Save "hustle_player" "leaguehustlestatsplayer" $common)

# yesterday's games: per-game tracking, hustle and advanced box scores
$sb = Save "scoreboard_$GameDate" "scoreboardv3" "GameDate=$GameDate&LeagueID=00"
if ($sb) {
    $games = @()
    try { $games = @((ConvertFrom-Json $sb).scoreboard.games | Where-Object { $_.gameStatus -eq 3 } | ForEach-Object { $_.gameId }) } catch { }
    foreach ($g in $games) {
        [void](Save "box_track_$g" "boxscoreplayertrackv3" "GameID=$g")
        [void](Save "box_hustle_$g" "boxscorehustlev2" "GameID=$g")
        [void](Save "box_advanced_$g" "boxscoreadvancedv3" "GameID=$g&StartPeriod=0&EndPeriod=0&StartRange=0&EndRange=0&RangeType=0")
    }
    Add-Content $log "games found: $($games.Count)"
}
Add-Content $log "done: $ok saved, $bad failed"
Write-Host "NBA tracking download: $ok saved, $bad failed. Details in $log"
