#!/usr/bin/env python3
"""check_catalog.py - refuse a catalog the 1.6X client would read differently than intended.

The client (cod1reloaded src/features/workshop.cpp) SKIPS an item it does not accept, in
silence for the player; this script applies the same rules so a mistake fails here, in
the pull request, instead.

    python tools/check_catalog.py [workshop.json] [--fetch]

--fetch also downloads every pk3 and compares its size and SHA-256 with the catalog
(the release asset must be uploaded first).
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")
FOLDER_RE = re.compile(r"^[A-Za-z0-9_-]{1,48}$")
FILE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,92}\.pk3$", re.I)
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_CATALOG = 512 * 1024
MAX_THUMB = 4 * 1024 * 1024


def fetch_check(url, size, sha):
    h = hashlib.sha256()
    got = 0
    req = urllib.request.Request(url, headers={"User-Agent": "cod1plus-workshop-check"})
    with urllib.request.urlopen(req, timeout=60) as r:
        for block in iter(lambda: r.read(1 << 20), b""):
            h.update(block)
            got += len(block)
            if got > size:
                return "larger than the catalog says"
    if got != size:
        return "size %d, catalog says %d" % (got, size)
    if h.hexdigest() != sha:
        return "sha256 %s, catalog says %s" % (h.hexdigest(), sha)
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fetch = "--fetch" in sys.argv
    path = args[0] if args else "workshop.json"
    root = os.path.dirname(os.path.abspath(path))
    errors = []
    if os.path.getsize(path) > MAX_CATALOG:
        errors.append("catalog larger than %d bytes (the client stops reading)" % MAX_CATALOG)
    with open(path, encoding="utf-8") as f:
        cat = json.load(f)
    items = cat.get("items")
    if not isinstance(items, list):
        print("FAIL: no \"items\" list")
        return 1
    if len(items) > 200:
        errors.append("more than 200 items (the client lists the first 200)")
    seen = set()
    for i, it in enumerate(items):
        where = "item %d (%s)" % (i, it.get("id", "?"))
        before = len(errors)
        def bad(msg):
            errors.append("%s: %s" % (where, msg))
        if not ID_RE.match(str(it.get("id", ""))):
            bad("id: letters, digits, _ - . only, 1-48 chars")
        elif it["id"] in seen:
            bad("duplicate id")
        seen.add(it.get("id"))
        if it.get("type", "map") not in ("map", "mod"):
            bad("type must be map or mod")
        if not FOLDER_RE.match(str(it.get("folder", "main"))):
            bad("folder: one plain folder name (main, a mod folder)")
        fn = str(it.get("file", ""))
        if not FILE_RE.match(fn) or fn in (".", ".."):
            bad("file: a bare *.pk3 name")
        elif re.match(r"^pak\d", fn, re.I) or fn.lower().startswith("localized_"):
            bad("file: the game's own paks cannot be replaced")
        size = it.get("size")
        if not isinstance(size, int) or size <= 0:
            bad("size: a positive integer (bytes)")
        sha = str(it.get("sha256", ""))
        if not SHA_RE.match(sha):
            bad("sha256: 64 lowercase hex digits")
        url = str(it.get("url", ""))
        if not url.startswith("https://"):
            bad("url: an https link (the public catalog never uses file:// or plain http)")
        m = re.match(r"^https://github\.com/[^/]+/[^/]+/releases/download/([^/]+)/([^/]+)$", url)
        if m and m.group(2) != fn:
            bad("url: the release asset is named %s, file says %s" % (m.group(2), fn))
        if m and it.get("version") and m.group(1) != "%s-%s" % (it.get("id"), it.get("version")):
            bad("url: release tag %s, expected %s-%s" % (m.group(1), it.get("id"), it.get("version")))
        for k, n in (("name", 64), ("author", 64), ("version", 24), ("description", 1500)):
            if len(str(it.get(k, ""))) > n:
                bad("%s longer than %d characters (cut by the client)" % (k, n))
        thumb = str(it.get("thumbnail", ""))
        if thumb and "://" not in thumb:
            tp = os.path.join(root, thumb)
            if not os.path.isfile(tp):
                bad("thumbnail %s is not in the repository" % thumb)
            elif os.path.getsize(tp) > MAX_THUMB:
                bad("thumbnail larger than 4 MB")
            elif os.path.splitext(tp)[1].lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
                bad("thumbnail: jpg, png or bmp")
        if fetch and len(errors) == before:
            err = fetch_check(url, size, sha)
            if err:
                bad("download: " + err)
            else:
                print("  %s: download matches (%d bytes)" % (it["id"], size))
    for e in errors:
        print("FAIL: " + e)
    print("%s: %d item(s), %s" % (path, len(items), "OK" if not errors else "%d problem(s)" % len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
