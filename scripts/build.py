#!/bin/env python3
import os
import re
import shutil
from pathlib import Path
from subprocess import CalledProcessError, check_call, check_output


def get_out(*args):
    return check_output(tuple(str(a) for a in args), text=True).strip()


def cmd(*args):
    return check_call(tuple(str(a) for a in args))


def get_slidev():
    try:
        return (get_out("which", "slidev"),)
    except CalledProcessError:
        return "npx", "slidev"


def get_repository():
    if repo := os.getenv("GITHUB_REPOSITORY"):
        return repo
    reg = re.compile("https://github.com/(\S+/\S+).git")
    return reg.match(get_out("git", "config", "--get", "remote.origin.url")).group(1)


def get_commit_hash():
    if commit := os.getenv("GITHUB_SHA"):
        return commit
    return get_out("git", "rev-parse", "HEAD")


def prepare_dist_dir(dist: Path):
    if dist.exists():
        shutil.rmtree(dist)
    cmd(
        "gh",
        "repo",
        "clone",
        get_repository(),
        dist,
        "--",
        "--branch",
        "gh-pages",
        "--depth",
        "1",
    )
    shutil.rmtree(dist / ".git", ignore_errors=True)


def build_slide(md: Path, dist: Path, base: str):
    assert md.is_file(), f"{md}: File not found."
    cmd(*get_slidev(), "build", md, "--out", dist, "--base", base, "--download")
    with open(dist / "commit", "w") as fp:
        fp.write(get_commit_hash())


def check_changes(md: Path, dist: Path):
    try:
        with open(dist / "commit") as fp:
            since = fp.read().strip()
            if get_out("git", "diff", "--name-only", since, "--", md):
                return True
            else:
                print(f"{md}:\n\tNo changes since {since}")
                return False
    except (FileNotFoundError, CalledProcessError) as e:
        print(f"{md}:\n\t{e}", flush=True)
        return True


if __name__ == "__main__":
    DIST = Path("dist")
    BASE = Path("/slides")
    SDIR = Path("src")

    if os.getenv("CI"):
        assert DIST.exists(), f"{DIST}: Directory not found."
    else:
        prepare_dist_dir(DIST)

    for md in SDIR.glob("*.md"):
        rel = md.absolute().relative_to(SDIR).with_suffix("")
        dist = DIST / rel

        if check_changes(md, dist):
            build_slide(md, dist, str(BASE / rel))
