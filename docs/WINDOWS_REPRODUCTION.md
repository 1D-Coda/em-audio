# Reproducing on Windows

One command. It fetches the repository, installs what it needs, checks your
machine, runs the pipeline, compares against the released results, and packs
everything into a zip to send back.

```powershell
irm https://raw.githubusercontent.com/1D-Coda/em-audio/main/tools/reproduce.ps1 -OutFile reproduce.ps1
.\reproduce.ps1
```

If PowerShell refuses to run a downloaded script, allow it for that session
only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Check first, run later

The environment check takes seconds, runs nothing, and names anything missing
along with the command to install it:

```powershell
.\reproduce.ps1 -Check
```

Do this first. A previous reproduction lost twenty minutes to a problem this
would have named in five seconds.

## What you need

| | install |
|---|---|
| Python 3.10+ | `winget install Python.Python.3.12` |
| Git, which also provides Git Bash | `winget install Git.Git` |
| FFmpeg | `winget install Gyan.FFmpeg` |
| Node | `winget install OpenJS.NodeJS` |
| eSpeak NG | `winget install eSpeak-NG.eSpeak-NG` |
| c2patool | from `github.com/contentauth/c2pa-rs/releases`, on your PATH |

`run_all.sh` is a bash script, so Git Bash or WSL is required. Git for Windows
provides Git Bash and the bootstrapper finds it in the usual install locations
even when it is not on your PATH.

Roughly twenty-five minutes, plus a 322 MB corpus download the first time.

## Honesty about this path

The PowerShell file is forty lines and has **never been executed on Windows**.
It finds Python and hands over; everything else is in
`tools/bootstrap_reproduction.py`, which was written and exercised on the
machine that produced it, including the clone, the dependency check, the
install, the self-test and the incomplete-checkout case.

That split is deliberate: the untested surface is those forty lines. If they
misbehave, skip them entirely, because the Python needs nothing from them:

```powershell
python tools\bootstrap_reproduction.py
```

Either way, send us the error rather than working around it. A bootstrapper
that fails on a real machine is a defect we want to know about.

## If it breaks, these are the usual reasons

**`$'\r': command not found`, or `set: pipefail: invalid option name`.** Your git
rewrote the shell scripts to Windows line endings on checkout. The repository
now carries a `.gitattributes` that prevents this, but an older clone will still
have it. The bootstrapper detects it and prints the fix.

**`python` opens the Microsoft Store.** That is the Store stub, not Python. Both
the script and the bootstrapper detect it and tell you to install the real one.

**The download fails with a connection error.** Older Windows PowerShell
negotiates TLS 1.0, which GitHub refuses. The script raises it to 1.2 before
downloading, so this should not happen; if it does, say so.

**`bash was not found`.** `run_all.sh` is a bash script. Install Git for
Windows, which provides Git Bash; the bootstrapper finds it in the usual
locations even when it is not on your PATH.

## What to send back

The script writes `EM_Audio_results_<date>.zip` and prints its path. It holds
your machine-readable results, your preflight report, both logs, and a record of
your platform and the exit codes.

Send it whatever the exit codes were. `verify_reproduction.py` exiting non-zero
means a deterministic output differs, which is a result we want, not a failure
on your part. The last reproduction exited non-zero and found two real defects
in the paper's declared numbers, and both are now published as findings.
