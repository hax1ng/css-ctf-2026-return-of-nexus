# Dead Faction Servers

**Category:** OSINT · **Points:** 10 · **Solves:** 349 · **Challenge ID:** 5

> The real access key is buried across two separate locations, split in half, one piece scrambled beyond plain sight.

## Challenge

> The old faction that ran Sector 9 didn't leave one trail — they left several, and most
> of them are decoys. Whoever built this infrastructure knew someone would come looking
> eventually, and buried the real access key across two separate locations, split in half,
> one piece scrambled beyond plain sight.
>
> Your recon has already surfaced their handle and at least one archived project. Don't
> trust the first thing you find — Sector 9's engineers were paranoid, and paranoid
> engineers plant false leads.
>
> Starting trace: `bobdev508`
> Flag Format: `CSSCTF{...}`

No file attachment — the only input is the handle `bobdev508`.

## Initial analysis

`bobdev508` resolves to a public **GitHub** profile with two repositories:

- `decoy-project`
- `dashboard-app`

The prompt telegraphs the structure of the solve: *most trails are decoys*, the real key is
*split in half across two locations*, and one half is *"scrambled beyond plain sight"*
(i.e. encoded). So the plan is: enumerate everything the handle owns — including history
and non-default branches — ignore anything that looks too easy, and assemble two fragments.

### The decoys

Three files sit in plain sight and each contains a flag-shaped string — but every one of
them uses the **wrong `CTF{...}` wrapper**, not `CSSCTF{...}`, and labels itself as
dummy/test data (committed under `evidence/`):

| File | Planted string |
|------|----------------|
| `decoy-project/old_config.txt` | `CTF{th1s_1s_n0t_th3_r34l_fl4g}` |
| `dashboard-app/app.py` | `CTF{n0t_qu1t3_1t}` |
| `dashboard-app/utils.py` | `CTF{4ls0_n0t_r34l}` |

The wrong prefix is the tell: these are the "false leads" the prompt warned about.

## Vulnerability / core concept

Classic **git history + branch archaeology**. The real secret was committed, then
"removed", and split so neither half is reachable from the current `main` tree:

- one half lives in a **deleted historical file**, Base64-encoded;
- the other half lives on a **non-default branch**.

`git clone` fetches history and all refs, so nothing is actually gone.

## Exploitation

Clone the two handle-owned repos and inspect every ref:

```console
$ git clone https://github.com/bobdev508/dashboard-app
$ cd dashboard-app
$ git log --all --oneline
5b3845b Add setup instructions to README
b72b7ff WIP: auth rework notes
99291d3 Remove committed secrets, oops      <-- deletion
be82c69 Add local env file                   <-- addition
457762d Add date helper
2421118 Add app entrypoint
56e1984 Initial commit
$ git branch -a
  remotes/origin/main
  remotes/origin/experimental/auth-rework    <-- non-default branch
```

**Fragment 1 — the scrambled half (deleted file, commit `be82c69`).** Commit `99291d3`
("Remove committed secrets, oops") deleted `.env.local`; the version from `be82c69` is
still in history:

```console
$ git show be82c69:.env.local
# local dev secrets, do not commit (oops)
SECRET_PART=Q1NTQ1RGe3VfZzA=

$ echo -n 'Q1NTQ1RGe3VfZzA=' | base64 -d
CSSCTF{u_g0
```

That is the flag prefix plus the first fragment. (Recovered copy committed at
`evidence/git-history/env.local__be82c69.txt`.)

**Fragment 2 — the second location (non-default branch).** The `experimental/auth-rework`
branch carries `auth_notes.md`:

```console
$ git show origin/experimental/auth-rework:auth_notes.md
...
bypass_suffix = "t_130d_508}"
```

(Recovered copy committed at `evidence/git-history/auth_notes.md__experimental-auth-rework.md`.)

**Assemble.** The two halves concatenate directly — no transformation beyond the Base64
decode:

```
CSSCTF{u_g0  +  t_130d_508}  =  CSSCTF{u_g0t_130d_508}
```

## Flag

```
CSSCTF{u_g0t_130d_508}
```

## Key takeaways

- On a GitHub-handle OSINT pivot, never stop at the working tree: `git log --all` + `git branch -a` surface deleted files and side branches where real secrets hide.
- Wrong flag wrapper = decoy. Here every plain-sight `CTF{...}` was a plant; the real key used `CSSCTF{...}` and was never present whole in any single file.
- "Split in half / scrambled beyond plain sight" literally meant: one Base64-encoded fragment in a deleted commit + one plaintext fragment on another branch.

## Files

- `evidence/decoy-project/`, `evidence/dashboard-app/` — the planted decoy files (working-tree copies).
- `evidence/git-history/` — the two recovered real fragments with their git provenance in-file.
- The cloned `.git` databases (pack files) are **not** committed; reproduce them by cloning the two public repos.
