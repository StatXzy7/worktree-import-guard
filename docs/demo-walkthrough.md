# 30–45 second demo walkthrough

Use the installed tool's built-in `--demo`. This script is a spoken/text guide for a screen recording;
the authoritative output is [demo-output.txt](demo-output.txt).

**Fixture type:** built-in teaching fixture with disposable directories (real Git worktrees when Git is
available). This is **not** a scan of the user's project.

## Script

1. **(0–5s)** Say: “Tests can pass while pytest imports another checkout. I'll run the built-in demo.”
   Command (replace `.venv` with your environment):

   ```powershell
   & ".venv\Scripts\wt-import.exe" --demo
   ```

2. **(5–20s)** Point to ordinary pytest passing, then `WORKTREE IMPORT GUARD: FAIL` with expected vs
   observed paths. Emphasize: tests passed, source did not.

3. **(20–35s)** Show the demo selecting the correct source inside the fixture and ending with
   `WORKTREE IMPORT GUARD: PASS`. Say this only proves the fixture's selected directories, not the
   user's machine.

4. **(35–45s)** Close: “On your project, install into the same pytest environment, run `--setup` once,
   then repeat with `wt-import -- -q`. UNKNOWN is not a pass.”

## Accessibility alternative

Readers who cannot watch video can follow [demo-output.txt](demo-output.txt) line by line; it is the
same recorded run with `<demo>` replacing temporary paths.
