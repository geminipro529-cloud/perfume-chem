# Tunnel Forensic Capture Runbook

Run read-only capture before applying integration patches. Do not reset, clean, checkout over, or overwrite the working tree.

```bash
git rev-parse --show-toplevel > tunnel_repo_root.txt
git branch --show-current > tunnel_branch.txt
git rev-parse HEAD > tunnel_head.txt
git remote -v > tunnel_remotes.txt
git status --porcelain=v2 -uall > tunnel_status_porcelain_v2.txt
git diff --binary > tunnel_worktree.patch
git diff --cached --binary > tunnel_index.patch
git stash list > tunnel_stashes.txt
git reflog --all --date=iso > tunnel_reflog.txt
git branch -a -vv > tunnel_branches.txt
git worktree list --porcelain > tunnel_worktrees.txt
git fsck --full --unreachable --no-reflogs > tunnel_unreachable_objects.txt
git ls-files --others --exclude-standard -z > tunnel_untracked_files.zlist
```

Archive untracked files from the generated NUL-delimited list without following unsafe paths; compute SHA-256 for every capture artifact. Include local run directories and Downloads candidates only as separate immutable strata.
