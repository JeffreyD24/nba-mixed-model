# Live line capture (on your computer)

Captures in-game lines and scores about every **30 seconds** (GitHub's checks only manage every 5 minutes).

**To run on a game night:** double-click **`Start_Live_Capture.bat`** any time before or during the games.
A window opens and prints a line every 30 seconds. Leave it open. It keeps the computer awake while it runs,
stops by itself when every game is final (or after 3 AM), and you can close the window any time to stop.

- Data goes to `live_capture\data\YYYY-MM-DD.csv`: one row per book (Consensus, DraftKings, FanDuel, Fanatics) whenever
  a line, price, score or quarter changes. Columns match `research/live/` in the repo.
- The laptop needs to be plugged in or charged, connected to the internet, and not shut. Closing the lid usually puts it to sleep
  regardless, so leave it open.
- Copy the data into the repo next session (Claude can do it from this folder).

Source: Action Network (refreshes about every 30 seconds, so checking faster would gain nothing).
