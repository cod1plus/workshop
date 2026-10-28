#!/usr/bin/env python3
"""make_catalog.py - add or update one item of a Workshop catalog (features/workshop.h).

Size and SHA-256 are computed from the pk3 itself, so the catalog always matches the
file that is uploaded next to it.

    python tools/workshop/make_catalog.py <catalog.json> --pk3 <file.pk3> --id mp_liberation
        --name Liberation --type map --version 26 --author "..." --description "..."
        --url <link to the pk3, absolute or relative to the catalog>
        [--thumbnail liberation.jpg] [--folder main] [--title "1.6X Workshop"]

A pack: --pack-dir DIR instead of --pk3 lists every pk3 of DIR (map / mod), or every png +
json of DIR for --type hud (the minimap's pictures, folder minimaps); --cvar NAME=VALUE
(repeatable, at most 4) is set by the client once the item is installed.

--url defaults to the pk3's file name (served next to the catalog). --github-release
OWNER/REPO instead links the asset of the release tagged <id>-<version> of that repo
(https://github.com/OWNER/REPO/releases/download/<id>-<version>/<file>), the layout of the
public catalog (cod1plus/workshop). The catalog file is created when missing; an item
with the same id is replaced, the others are kept.
"""
import argparse
import hashlib
import json
import os
import sys


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("catalog")
    ap.add_argument("--pk3", help="the item's one pk3")
    ap.add_argument("--pack-dir", help="a pack instead: every *.pk3 (map / mod) or *.png + *.json (hud) of DIR")
    ap.add_argument("--cvar", action="append", default=[], metavar="NAME=VALUE", help="seta'd once installed (at most 4)")
    ap.add_argument("--id", required=True)
    ap.add_argument("--name")
    ap.add_argument("--type", choices=["map", "mod", "hud"], default="map")
    ap.add_argument("--version", default="")
    ap.add_argument("--author", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--folder", default="main")
    ap.add_argument("--file", help="name it gets in the game folder (default: the pk3's name)")
    ap.add_argument("--url")
    ap.add_argument("--github-release", metavar="OWNER/REPO")
    ap.add_argument("--thumbnail", default="")
    ap.add_argument("--title")
    a = ap.parse_args()

    if os.path.exists(a.catalog):
        with open(a.catalog, encoding="utf-8") as f:
            cat = json.load(f)
    else:
        cat = {"title": "1.6X Workshop", "items": []}
    if a.title:
        cat["title"] = a.title

    if bool(a.pk3) == bool(a.pack_dir):
        ap.error("one of --pk3 or --pack-dir")
    if a.github_release and not a.version:
        ap.error("--github-release needs --version (the release tag is <id>-<version>)")

    def link(file_name):
        if a.github_release:
            return "https://github.com/%s/releases/download/%s-%s/%s" % (a.github_release, a.id, a.version, file_name)
        return (a.url.rstrip("/") + "/" + file_name) if (a.url and a.pack_dir) else (a.url or file_name)

    item = {
        "id": a.id,
        "type": a.type,
        "name": a.name or a.id,
        "author": a.author,
        "version": a.version,
        "description": a.description,
        "folder": "minimaps" if a.type == "hud" else a.folder,
    }
    if a.pk3:
        file_name = a.file or os.path.basename(a.pk3)
        item.update({"file": file_name, "size": os.path.getsize(a.pk3), "sha256": sha256_of(a.pk3), "url": link(file_name)})
    else:
        exts = (".png", ".json") if a.type == "hud" else (".pk3",)
        names = sorted(n for n in os.listdir(a.pack_dir) if n.lower().endswith(exts))
        if not names or len(names) > 32:
            ap.error("--pack-dir: 1 to 32 files (%d found)" % len(names))
        item["files"] = [{"file": n, "size": os.path.getsize(os.path.join(a.pack_dir, n)),
                          "sha256": sha256_of(os.path.join(a.pack_dir, n)), "url": link(n)} for n in names]
    if a.cvar:
        item["cvars"] = dict(c.split("=", 1) for c in a.cvar[:4])
    if a.thumbnail:
        item["thumbnail"] = a.thumbnail
    items = [it for it in cat.get("items", []) if it.get("id") != a.id]
    items.append(item)
    cat["items"] = items
    with open(a.catalog, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for f in item.get("files", [item]):
        print("%s: %s %d bytes sha256 %s" % (a.catalog, f["file"], f["size"], f["sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
