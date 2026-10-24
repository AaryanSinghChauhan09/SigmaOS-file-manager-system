"""File manager for SigmaOS-file-manager-system (inspired by nemo and omafind).

Principles: deterministic listing (sorted), depth-limited search, type-aware
action menus, a pure trash plan (with collision-safe names) separate from the
thin apply layer, fail-fast on missing entries.
"""
import argparse, fnmatch, os, sys, tempfile

ENGINE = {
    "name": "sigma-files",
    "summary": "File manager: list, search, tabs, actions, trash planning",
    "language": "python",
    "verbs": ["list", "search", "tabs-plan", "actions", "trash-plan"],
    "principles": ["Least Astonishment", "Defensive Programming", "Fail-Fast",
                   "KISS", "Separation of Concerns", "Deterministic Testing"],
}

cli_doc = """\
$ sigma-files list ~/Documents
$ sigma-files search ~/Documents --pattern "*.md" --max-depth 3
$ sigma-files tabs-plan ~/Documents ~/Downloads
$ sigma-files actions report.pdf
$ sigma-files trash-plan ~/Documents --name old.txt --name draft.md
"""

EXT_ACTIONS = {
    ".txt": ["open", "edit", "rename", "compress", "trash"],
    ".md": ["open", "edit", "rename", "trash"],
    ".pdf": ["open", "view", "print", "rename", "trash"],
    ".png": ["open", "view", "rotate", "set-wallpaper", "trash"],
    ".jpg": ["open", "view", "rotate", "set-wallpaper", "trash"],
    ".jpeg": ["open", "view", "rotate", "set-wallpaper", "trash"],
    ".svg": ["open", "view", "edit", "trash"],
    ".mp3": ["open", "play", "tag", "trash"],
    ".ogg": ["open", "play", "tag", "trash"],
    ".mp4": ["open", "play", "trim", "trash"],
    ".mkv": ["open", "play", "trim", "trash"],
    ".zip": ["open", "extract", "compress", "trash"],
    ".tar": ["open", "extract", "compress", "trash"],
    ".gz": ["open", "extract", "trash"],
    ".iso": ["write-to-usb", "mount", "verify", "properties"],
    ".sh": ["open", "edit", "run", "properties"],
}
DIR_ACTIONS = ["enter", "new-tab", "search-here", "compress", "properties"]


class FmError(ValueError):
    pass


def list_dir(path, show_hidden=False):
    """Sorted directory listing with kinds and sizes. Fail-fast on non-dirs."""
    if not os.path.isdir(path):
        raise FmError(f"not a directory: {path}")
    entries = []
    for name in sorted(os.listdir(path)):
        if not show_hidden and name.startswith("."):
            continue
        full = os.path.join(path, name)
        if os.path.isdir(full):
            entries.append({"name": name, "kind": "dir", "size": None})
        else:
            entries.append({"name": name, "kind": "file", "size": os.path.getsize(full)})
    return entries


def search(root, pattern, max_depth=4, show_hidden=False):
    """Depth-limited recursive name search. Deterministic (sorted) results."""
    if not os.path.isdir(root):
        raise FmError(f"not a directory: {root}")
    if max_depth < 0:
        raise FmError(f"max-depth must be >= 0, got {max_depth}")
    hits = []

    def rec(cur, depth):
        if depth > max_depth:
            return
        for name in sorted(os.listdir(cur)):
            if not show_hidden and name.startswith("."):
                continue
            full = os.path.join(cur, name)
            rel = os.path.relpath(full, root)
            if fnmatch.fnmatch(name.lower(), pattern.lower()):
                hits.append(rel)
            if os.path.isdir(full):
                rec(full, depth + 1)

    rec(root, 0)
    return sorted(hits)


def tabs_plan(paths):
    """Plan a set of tabs (one per existing path). Pure-ish: validates paths."""
    if not paths:
        raise FmError("no paths given")
    tabs = []
    seen = set()
    for p in paths:
        full = os.path.abspath(os.path.expanduser(p))
        if not os.path.isdir(full):
            raise FmError(f"not a directory: {p}")
        if full in seen:
            continue  # least astonishment: drop duplicate tabs
        seen.add(full)
        tabs.append({"index": len(tabs), "path": full,
                     "label": os.path.basename(full) or full})
    return tabs


def actions_for(path):
    """Type-aware action list for a path (pure)."""
    if os.path.isdir(path):
        return list(DIR_ACTIONS)
    ext = os.path.splitext(path)[1].lower()
    return list(EXT_ACTIONS.get(ext, ["open", "rename", "compress", "trash"]))


def trash_plan(root, names, trash_dir):
    """Pure plan: (src, dst) pairs with collision-safe destination names."""
    if not os.path.isdir(root):
        raise FmError(f"not a directory: {root}")
    pairs, taken = [], set()
    for name in sorted(names):
        src = os.path.join(root, name)
        if not os.path.exists(src):
            raise FmError(f"no such entry: {name}")
        dst = os.path.join(trash_dir, os.path.basename(src))
        n = 1
        while dst in taken or os.path.exists(dst):
            stem, ext = os.path.splitext(os.path.basename(src))
            dst = os.path.join(trash_dir, f"{stem}-{n}{ext}")
            n += 1
        taken.add(dst)
        pairs.append((src, dst))
    return pairs


def apply_trash(pairs):
    """Apply layer: move entries to the trash dir. Fail-fast on disappearance."""
    for src, dst in pairs:
        if not os.path.exists(src):
            raise FmError(f"vanished before trash: {src}")
    done = 0
    for src, dst in pairs:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(src, dst)
        done += 1
    return done


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    sub = p.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="list a directory (sorted)")
    ls.add_argument("path")
    ls.add_argument("--hidden", action="store_true", help="include dotfiles")
    se = sub.add_parser("search", help="recursive name search")
    se.add_argument("root")
    se.add_argument("--pattern", required=True, help='glob like "*.md"')
    se.add_argument("--max-depth", type=int, default=4)
    se.add_argument("--hidden", action="store_true")
    tp = sub.add_parser("tabs-plan", help="plan tabs for one or more directories")
    tp.add_argument("paths", nargs="+")
    ac = sub.add_parser("actions", help="type-aware actions for a path")
    ac.add_argument("path")
    tr = sub.add_parser("trash-plan", help="plan (or apply) moving entries to trash")
    tr.add_argument("root")
    tr.add_argument("--name", action="append", required=True, dest="names")
    tr.add_argument("--trash-dir", default=os.path.expanduser("~/.local/share/Trash/files"))
    tr.add_argument("--apply", action="store_true", help="actually move entries")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "list":
            for e in list_dir(args.path, show_hidden=args.hidden):
                size = "-" if e["size"] is None else str(e["size"])
                print(f"{e['kind'][0]} {e['name']}\t{size}")
        elif args.cmd == "search":
            hits = search(args.root, args.pattern, max_depth=args.max_depth,
                          show_hidden=args.hidden)
            if not hits:
                print("no matches")
            for h in hits:
                print(h)
        elif args.cmd == "tabs-plan":
            for t in tabs_plan(args.paths):
                print(f"tab {t['index']}: {t['label']} ({t['path']})")
        elif args.cmd == "actions":
            print(" ".join(actions_for(args.path)))
        elif args.cmd == "trash-plan":
            pairs = trash_plan(args.root, args.names, args.trash_dir)
            if args.apply:
                n = apply_trash(pairs)
                print(f"trashed {n} entr(y/ies)", file=sys.stderr)
            verb = "trashed" if args.apply else "would trash"
            for src, dst in pairs:
                print(f"{verb} {os.path.basename(src)} -> {dst}")
        return 0
    except (FmError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def self_test() -> None:
    with tempfile.TemporaryDirectory() as d:
        docs = os.path.join(d, "docs")
        deep = os.path.join(docs, "deep")
        os.makedirs(deep)
        files = {
            os.path.join(d, "a.txt"): "aaa",
            os.path.join(d, "b.png"): "bb",
            os.path.join(d, ".hidden.txt"): "h",
            os.path.join(docs, "c.md"): "ccc",
            os.path.join(deep, "d.txt"): "dddd",
            os.path.join(deep, "e.pdf"): "x",
        }
        for path, body in files.items():
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        # listing: sorted, kinds, sizes, hidden excluded by default
        ents = list_dir(d)
        assert [e["name"] for e in ents] == ["a.txt", "b.png", "docs"]
        assert [e["kind"] for e in ents] == ["file", "file", "dir"]
        assert ents[0]["size"] == 3
        assert [e["name"] for e in list_dir(d, show_hidden=True)][0] == ".hidden.txt"
        try:
            list_dir(os.path.join(d, "nope"))
        except FmError:
            pass
        else:
            raise AssertionError("listing a non-dir not caught")
        # search: depth-limited, glob, deterministic, hidden excluded
        assert search(d, "*.txt") == ["a.txt", os.path.join("docs", "deep", "d.txt")]
        assert search(d, "*.txt", max_depth=1) == ["a.txt"]
        assert search(d, "*.txt", max_depth=0) == ["a.txt"]
        assert search(d, "*.TXT") == ["a.txt", os.path.join("docs", "deep", "d.txt")]
        assert search(d, "*.zip") == []
        assert ".hidden.txt" in search(d, "*.txt", show_hidden=True)
        assert ".hidden.txt" not in search(d, "*.txt")   # hidden by default
        try:
            search(d, "*.txt", max_depth=-1)
        except FmError:
            pass
        else:
            raise AssertionError("negative depth not caught")
        # tabs: validated, de-duplicated
        tabs = tabs_plan([docs, d, docs])
        assert [t["label"] for t in tabs] == ["docs", os.path.basename(d)]
        assert [t["index"] for t in tabs] == [0, 1]
        try:
            tabs_plan([])
        except FmError:
            pass
        else:
            raise AssertionError("empty tabs not caught")
        # actions: type-aware
        assert "enter" in actions_for(docs)
        assert "edit" in actions_for(os.path.join(d, "a.txt"))
        assert "view" in actions_for(os.path.join(d, "b.png"))
        assert "write-to-usb" in actions_for("/tmp/x.iso")
        assert "compress" in actions_for("/tmp/x.weird")   # generic fallback
        # trash planning: pure, collision-safe, dry-run leaves nothing behind
        trash = os.path.join(d, "trash")
        os.makedirs(trash)
        with open(os.path.join(trash, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("existing")            # pre-existing collision
        pairs = trash_plan(d, ["a.txt", "b.png"], trash)
        assert [(os.path.basename(s), os.path.basename(t)) for s, t in pairs] == \
            [("a.txt", "a-1.txt"), ("b.png", "b.png")]
        assert os.path.exists(os.path.join(d, "a.txt"))   # dry-run touched nothing
        try:
            trash_plan(d, ["ghost.txt"], trash)
        except FmError:
            pass
        else:
            raise AssertionError("trashing a missing entry not caught")
        # apply layer (inside the tempdir only)
        assert apply_trash(pairs) == 2
        assert not os.path.exists(os.path.join(d, "a.txt"))
        assert open(os.path.join(trash, "a-1.txt"), encoding="utf-8").read() == "aaa"
        assert open(os.path.join(trash, "b.png"), encoding="utf-8").read() == "bb"
        assert open(os.path.join(trash, "a.txt"), encoding="utf-8").read() == "existing"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
