#!/usr/bin/env python3
"""Stop hook — nudge Claude to save a session wrap-up if nothing saved yet.

Fires when Claude is about to stop. Checks whether anything was saved during
this session (via AXE_SESSION_ID). If nothing was saved, blocks the stop and
asks Claude to save a 1-2 sentence wrap-up before finishing. If the session
already has saves (or no key/session-id), exits cleanly and lets Claude stop.

Wire it (per teammate, via install.sh into ~/.claude/settings.json):
  "hooks": { "Stop": [ { "hooks": [ {
      "type": "command",
      "command": "python3 ~/imi-memory-kit/hooks/session_stop_memory.py"
  } ] } ] }
"""
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request

ATLAS = os.environ.get("AXE_MEMORY_URL", "https://atlas.axe.observer").rstrip("/")
SESSION = os.environ.get("AXE_SESSION_ID", "").strip()
_SSL = ssl._create_unverified_context()


def _brand():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "kit.conf")
    try:
        for line in open(p):
            line = line.strip()
            if line.startswith("BRAND=") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "AXE"


BRAND = _brand()
KEY = (os.environ.get(BRAND + "_MEMORY_KEY")
       or os.environ.get(BRAND + "_API_KEY")
       or os.environ.get("AXE_API_KEY") or "").strip()


def _session_has_saves() -> bool:
    """Return True if anything was saved in this session (don't nag if so)."""
    if not KEY or not SESSION:
        return True  # can't check — don't interrupt
    try:
        headers = {"Content-Type": "application/json", "X-API-Key": KEY}
        qs = urllib.parse.urlencode({"session": SESSION, "limit": 1, "mine": "1"})
        req = urllib.request.Request(
            ATLAS + "/api/memory/recall?" + qs, method="GET", headers=headers
        )
        d = json.loads(urllib.request.urlopen(req, timeout=5, context=_SSL).read())
        count = (d.get("data") or {}).get("count") or 0
        return count > 0
    except Exception:
        return True  # on error, let Claude stop cleanly


def main():
    # Consume stdin (hook may pipe JSON payload — discard it gracefully)
    try:
        if not sys.stdin.isatty():
            json.load(sys.stdin)
    except Exception:
        pass

    if _session_has_saves():
        print("{}")
        return

    cli = BRAND.lower() + "-memory"
    tags = BRAND.lower()
    print(json.dumps({
        "continue": True,
        "userMessage": (
            f"Before stopping: if any decisions, findings, or client preferences came up "
            f"in this session, save them to team memory now so teammates have the context.\n\n"
            f"Run: `{cli} save \"<1-2 sentence summary>\" --kind decision --share --tags {tags}`\n\n"
            f"If there is genuinely nothing worth saving from this session, just say so and stop."
        )
    }))


if __name__ == "__main__":
    main()
