# cod1plus workshop

The catalog behind the **Workshop** tab of the COD1.6X client (Ctrl+M > Workshop): maps
and mods a player installs in one click. The client reads `workshop.json` from this
repository (`https://raw.githubusercontent.com/cod1plus/workshop/main/workshop.json`),
shows each item with its picture, downloads the pk3, checks its SHA-256 and puts it in
its folder (`main` for a map).

- `workshop.json` - the catalog (format below).
- `thumbs/` - one picture per item, 16:9 (640x360 is plenty), jpg or png.
- the pk3s are **release assets**, one release per item version, tagged `<id>-<version>`
  (GitHub refuses files over 100 MB in the repository; a release asset can be 2 GB).

## Adding a map, or a new version of one

1. Create a release tagged `<id>-<version>` (e.g. `mp_liberation-28`) and upload the pk3
   as its asset, under the exact name the game uses (`zz_mp_liberation.pk3`).
2. Put its picture in `thumbs/<id>.jpg` (a new picture: a new file name, clients cache
   pictures by link).
3. Write the item from the pk3 itself (size and SHA-256 are computed, the release link
   is built from id + version):
   ```
   python tools/make_catalog.py workshop.json --pk3 <path>/zz_mp_liberation.pk3 \
       --id mp_liberation --name Liberation --type map --version 28 \
       --author "..." --description "..." --thumbnail thumbs/mp_liberation.jpg \
       --github-release cod1plus/workshop
   ```
4. `python tools/check_catalog.py` (the same check runs on every push and pull request;
   run the workflow by hand with *fetch* to download the asset and verify its hash).
5. Commit to `main`. Clients pick it up the next time the tab loads the catalog (the
   raw link is cached by GitHub for a few minutes).

A player who has the previous version sees **UPDATE**; the client replaces the file only
when the download matches the catalog's SHA-256. A pk3 the game has open is swapped in at
the next launch. CoD1 lists its pk3s when it starts: a new map is playable after a restart.

## Format

```json
{ "title": "1.6X Workshop",
  "items": [ { "id": "mp_liberation", "type": "map", "name": "Liberation",
               "author": "...", "version": "27", "description": "...",
               "folder": "main", "file": "zz_mp_liberation.pk3",
               "size": 191876653, "sha256": "<64 hex>",
               "url": "https://github.com/cod1plus/workshop/releases/download/mp_liberation-27/zz_mp_liberation.pk3",
               "thumbnail": "thumbs/mp_liberation.jpg" } ] }
```

`id` letters, digits, `_ - .` (48 max) - `type` map or mod - `folder` one folder name
(default `main`) - `file` a bare `.pk3` name, never the game's own `pak*` / `localized_*`
- `url` https - `thumbnail` relative to this repository or https. An item breaking a rule
is skipped by the client: `check_catalog.py` is there so it fails here instead.
