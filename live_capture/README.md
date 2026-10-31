# Live line capture (on your computer)

Captures in-game lines and scores about every **30 seconds** (GitHub's checks only manage every 5 minutes).

**Easiest: run it automatically every night.** Double-click **`Install_Nightly_Capture.bat`** once. It creates a Windows
scheduled task ("NBA live line capture") that starts the capture at 6:45 PM every day, wakes the laptop if it's asleep, and
stops when the night's games are final. `Remove_Nightly_Capture.bat` undoes it.

**For it to keep running all night** (Oct 30 stopped at 10:01 PM, most likely because the laptop went to sleep):
- Keep the laptop **plugged in**.
- Settings → System → Power & battery → **Screen and sleep**: set "When plugged in, put my device to sleep after" to **Never**.
- Control Panel → Hardware and Sound → Power Options → **Choose what closing the lid does**: "When I close the lid" (Plugged in)
  → **Do nothing**. Otherwise closing the lid sleeps the laptop no matter what the script asks.
- The screen can turn off; that's fine.

**To run it by hand instead:** double-click **`Start_Live_Capture.bat`** any time before or during the games.
A window opens and prints a line every 30 seconds. Leave it open. It keeps the computer awake while it runs,
stops by itself when every game is final (or after 3 AM), and you can close the window any time to stop.

- Data goes to `live_capture\data\YYYY-MM-DD.csv`: one row per book (Consensus, DraftKings, FanDuel, Fanatics) whenever
  a line, price, score or quarter changes. Columns match `research/live/` in the repo.
- The laptop needs to be plugged in or charged, connected to the internet, and not shut. Closing the lid usually puts it to sleep
  regardless, so leave it open.
- Halves, 1st quarter and team totals go to `live_capture\data\periods_YYYY-MM-DD.csv`: one row per game, period
  (game, firsthalf, secondhalf, firstquarter) and book, at nine books, whenever a line or price changes, for games not yet final.
  Values are saved exactly as posted (a few books sometimes post odd totals; those get filtered in analysis).
- Copy the data into the repo next session (Claude can do it from this folder).

Source: Action Network (refreshes about every 30 seconds, so checking faster would gain nothing).
