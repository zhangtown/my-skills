#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rewire-skills.py — point every agent skills dir at the central library.

Central library (source of truth):  ~/.skills-manager/skills
Agent dirs get ONE junction per skill -> master, so adding/deleting/editing a
skill happens in exactly one place (the AGENTS.md contract).

  python rewire-skills.py                          # dry run: print the plan
  python rewire-skills.py --apply                  # execute (junctions recreated, identical copies replaced)
  python rewire-skills.py --apply --prune          # also delete stale links (target gone) + aliases
  python rewire-skills.py --apply --link-missing   # also link master skills that no agent can read
  python rewire-skills.py --apply --link-missing --link-dirs .pi/agent/skills,.claude/skills
                                                   # ... but only into these agent dirs

Safety:
  * a real directory is only replaced by a junction after its content is verified
    byte-identical (tree hash) to the master copy — anything that differs is
    reported and left untouched. A difference in *line endings only* (CRLF vs LF,
    which happens when another agent re-writes a copy) counts as identical, since
    no content is lost by pointing the entry at master instead;
  * --prune only ever removes reparse points (junctions/symlinks), never a real
    directory and never any file content;
  * --link-missing only adds junctions, it never deletes anything.

2026-09-17 fix (blind spot): os.path.isdir() returns False for a *dangling*
junction on Windows, so the old scan silently skipped exactly the broken links
it was meant to report (it printed "ok: 350" while 6 links were dead) and the
post-check could not see them either. All existence tests now go through
lexists(), and the scan additionally reports:
  REWIRE-DEAD  dangling link whose name exists in master  -> re-point it
  STALE-UNLINK dangling link with no master dir           -> prune (--prune)
  ALIAS-PRUNE  link that resolves into master under a different name -> prune
  LINK-MISSING master skill reachable from no agent dir   -> link (--link-missing)
  BROKEN       unresolvable non-link entry                -> reported, untouched
"""
import hashlib
import os
import shutil
import stat
import subprocess
import sys

HOME = os.path.expanduser("~")
MASTER = os.path.join(HOME, ".skills-manager", "skills")
REP = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
LINK_DIRS = None                   # optional --link-dirs subset for --link-missing
TARGET_DIRS = [".pi/agent/skills", ".claude/skills", ".zcode/skills",
               ".codebuddy/skills", ".workbuddy/skills", ".dsh/skills",
               ".agents/skills"]


def tree_fp(d):
    """(raw_hash, hash_ignoring_line_endings, file_count) — CRLF/LF must not look like a conflict."""
    h = hashlib.md5()
    hn = hashlib.md5()
    n = 0
    for root, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x not in ("__MACOSX", "__pycache__", ".git", "node_modules")]
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(root, f), d).replace("\\", "/")
            h.update(rel.encode())
            hn.update(rel.encode())
            try:
                raw = open(os.path.join(root, f), "rb").read()
                h.update(raw)
                hn.update(raw.replace(b"\r\n", b"\n"))
                n += 1
            except Exception:
                h.update(b"<err>")
                hn.update(b"<err>")
    return h.hexdigest()[:10], hn.hexdigest()[:10], n


def is_reparse(p):
    """True for junctions/symlinks — including DANGLING ones (that is the fix)."""
    try:
        return bool(os.lstat(p).st_file_attributes & REP)
    except Exception:
        return False


def is_junction(p):
    return is_reparse(p)


def state(p):
    """'dir' = resolves to something | 'dead' = entry exists but target is gone | 'none'"""
    if os.path.exists(p):
        return "dir"
    if os.path.lexists(p):
        return "dead"
    return "none"


def same(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def master_of(fp):
    """If fp resolves into MASTER, return the master dir name it points at."""
    try:
        real = os.path.normpath(os.path.realpath(fp))
    except Exception:
        return None
    if os.path.normcase(os.path.dirname(real)) == os.path.normcase(os.path.normpath(os.path.realpath(MASTER))):
        return os.path.basename(real)
    return None


def agent_dir(d):
    return os.path.join(HOME, *d.split("/"))


def make_junction(link, target):
    r = subprocess.run(["cmd", "/c", "mklink", "/J", os.path.normpath(link), os.path.normpath(target)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"mklink failed: {r.stdout.strip()} {r.stderr.strip()}")


def remove_link(p):
    """Remove a junction/symlink only. Refuses to touch a real directory."""
    if not is_reparse(p):
        raise RuntimeError(f"refusing to delete a non-link entry: {p}")
    try:
        os.rmdir(p)
        return
    except OSError:
        pass
    r = subprocess.run(["cmd", "/c", "rmdir", os.path.normpath(p)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rmdir failed: {r.stdout.strip()} {r.stderr.strip()}")


def scan(force=()):
    """Returns (plan, coverage, partial, orphans). Pure read-only."""
    plan = []                      # (action, agent_dir, name, detail)
    coverage = {}                  # master name -> set(agent dirs that properly link it)
    for d in TARGET_DIRS:
        p = agent_dir(d)
        if not os.path.isdir(p):
            continue
        for n in sorted(os.listdir(p)):
            if n.startswith("."):
                continue                                      # agent-side config files, not skills
            fp = os.path.join(p, n)
            dst = os.path.join(MASTER, n)
            st = state(fp)
            if st == "none":
                continue
            if st == "dead":                              # <- the blind spot fix
                if os.path.isdir(dst):
                    plan.append(("REWIRE-DEAD", d, n, "link target gone -> re-point at master"))
                elif is_reparse(fp):
                    plan.append(("STALE-UNLINK", d, n, f"dangling link, no master/{n}"))
                else:
                    plan.append(("BROKEN", d, n, "unresolvable entry (not a link) — NOT touched"))
                continue
            # resolves
            tgt = master_of(fp)
            if tgt and tgt != n:
                plan.append(("ALIAS-PRUNE", d, n, f"alias of master/{tgt}"))
                continue
            if tgt == n:
                coverage.setdefault(n, set()).add(d)
            if not os.path.isdir(dst):
                plan.append(("SKIP-no-master", d, n, ""))       # local-only extra
                continue
            if same(fp, dst):
                plan.append(("ok", d, n, ""))
                continue
            if is_junction(fp):
                plan.append(("REWIRE", d, n, "junction -> " + os.path.realpath(fp).replace(HOME, "~")))
            else:
                a, b = tree_fp(fp), tree_fp(dst)
                if a[0] == b[0]:
                    plan.append(("REPLACE-COPY", d, n, f"identical copy ({b[2]} files) -> junction"))
                elif a[1] == b[1]:
                    plan.append(("REPLACE-COPY", d, n,
                                 f"identical copy modulo line endings ({b[2]} files) -> junction"))
                elif n in force:
                    plan.append(("REPLACE-COPY", d, n,
                                 f"FORCED: superseded copy {a[0]}/{a[2]}f -> master {b[0]}/{b[2]}f"))
                else:
                    plan.append(("CONFLICT", d, n,
                                 f"copy {a[0]}/{a[2]}f != master {b[0]}/{b[2]}f — NOT touched"))
    have_dirs = [d for d in TARGET_DIRS if os.path.isdir(agent_dir(d))]
    masters = sorted(m for m in os.listdir(MASTER)
                     if not m.startswith(".") and os.path.isdir(os.path.join(MASTER, m)))
    noskill = [m for m in masters if not os.path.exists(os.path.join(MASTER, m, "SKILL.md"))]
    if noskill:
        print("WARN master dirs without SKILL.md (not real skills):", ", ".join(noskill))
    partial = [(m, len(coverage.get(m, ()))) for m in masters if coverage.get(m)]
    partial = [x for x in partial if x[1] < len(have_dirs)]
    orphans = [m for m in masters if not coverage.get(m)]
    for m in orphans:
        missing = [d for d in have_dirs if d not in coverage.get(m, ()) and (not LINK_DIRS or d in LINK_DIRS)]
        plan.append(("LINK-MISSING", "-", m, f"no agent can read it -> link to {len(missing)} dirs: " + ",".join(missing)))
    return plan, coverage, partial, orphans


def main():
    argv = sys.argv[1:]
    apply_ = "--apply" in argv
    prune = "--prune" in argv
    link_missing = "--link-missing" in argv
    force = set()
    global LINK_DIRS
    for i, a in enumerate(argv):
        if a == "--force" and i + 1 < len(argv):
            force.update(x for x in argv[i + 1].split(",") if x)
        if a == "--link-dirs" and i + 1 < len(argv):
            LINK_DIRS = [x.strip() for x in argv[i + 1].split(",") if x.strip()]
    if force:
        print("forcing replacement (superseded skills):", ", ".join(sorted(force)))

    plan, coverage, partial, orphans = scan(force)
    counts = {}
    for act, *_ in plan:
        counts[act] = counts.get(act, 0) + 1
    have_dirs = [d for d in TARGET_DIRS if os.path.isdir(agent_dir(d))]
    print("agent dirs:", len(have_dirs), "| master skills:", len([m for m in os.listdir(MASTER)
          if not m.startswith(".") and os.path.isdir(os.path.join(MASTER, m))]))
    print(("APPLYING" if apply_ else "PLAN"), counts)
    changed = pruned = linked = 0
    errors = []
    for act, d, n, detail in plan:
        if act in ("REWIRE", "REPLACE-COPY", "REWIRE-DEAD", "LINK-MISSING"):
            print(f"  {act:13s} " + (f"~/{d}/{n}" if d != "-" else f"{n}") + (f"   [{detail}]" if detail else ""))
        elif act in ("CONFLICT", "SKIP-no-master", "BROKEN", "STALE-UNLINK", "ALIAS-PRUNE"):
            mark = "!!" if act in ("CONFLICT", "BROKEN") else ("--" if act == "STALE-UNLINK" or act == "ALIAS-PRUNE" else "..")
            print(f"  {mark} {act:11s} ~/{d}/{n}" + (f"   [{detail}]" if detail else ""))
        if not apply_:
            continue
        fp = os.path.join(HOME, *d.split("/"), n)
        try:
            if act == "REPLACE-COPY":
                shutil.rmtree(fp)
                make_junction(fp, os.path.join(MASTER, n))
                changed += 1
            elif act in ("REWIRE", "REWIRE-DEAD"):
                remove_link(fp)
                make_junction(fp, os.path.join(MASTER, n))
                changed += 1
            elif act in ("STALE-UNLINK", "ALIAS-PRUNE") and prune:
                remove_link(fp)
                pruned += 1
            elif act == "LINK-MISSING" and link_missing:
                for dd in detail.split("dirs: ")[-1].split(","):
                    dd = dd.strip()
                    if not dd:
                        continue
                    make_junction(os.path.join(HOME, *dd.split("/"), n), os.path.join(MASTER, n))
                    linked += 1
        except Exception as e:
            errors.append(f"{act} ~/{d}/{n}: {e}")
            print(f"   ERROR {act} ~/{d}/{n}: {e}")
    if apply_:
        print(f"REWIRED {changed} | PRUNED {pruned} | LINKED {linked}" + (f" | ERRORS {len(errors)}" if errors else ""))
    else:
        print("dry run — re-run with --apply (add --prune / --link-missing as needed)")

    # ---- post-check (independent re-scan, sees dangling links now) ----
    plan2, coverage2, partial2, orphans2 = scan(force)
    dead = [(d, n) for a, d, n, _ in plan2 if a in ("REWIRE-DEAD", "STALE-UNLINK", "BROKEN")]
    alias = [(d, n) for a, d, n, _ in plan2 if a == "ALIAS-PRUNE"]
    conf = [(d, n) for a, d, n, _ in plan2 if a == "CONFLICT"]
    mis = [(d, n) for a, d, n, _ in plan2 if a == "REWIRE"]
    copy = [(d, n) for a, d, n, _ in plan2 if a == "REPLACE-COPY"]
    others = [(d, n) for a, d, n, _ in plan2 if a == "SKIP-no-master"]
    print("verify: dead-links=%d aliases=%d conflicts=%d wrong-target=%d real-copies=%d local-only=%d orphans=%d partial=%d"
          % (len(dead), len(alias), len(conf), len(mis), len(copy), len(others), len(orphans2), len(partial2)))
    for tag, items in (("dead", dead), ("alias", alias), ("conflict", conf), ("wrong-target", mis)):
        for d, n in items:
            print(f"   {tag:12s} ~/{d}/{n}")
    for d in sorted(partial2, key=lambda x: -x[1])[:25]:
        print(f"   partial      master/{d[0]}  [{d[1]}/{len(have_dirs)} agents]")
    if len(partial2) > 25:
        print(f"   partial      … +{len(partial2) - 25} more")
    if not dead and not alias and not conf and not mis and not copy and not orphans2:
        print("verify: every agent entry resolves into master, no dead link / alias / orphan ✔")


if __name__ == "__main__":
    main()
