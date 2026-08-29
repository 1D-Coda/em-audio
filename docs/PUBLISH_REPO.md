# Publishing this repository

There is no remote yet, so nothing here has been cloned by anyone and the
history can still be corrected. That stops being true the moment it is pushed.

## Fix this first: the voice model is in the history

`DATA_LICENSES.md` and the manuscript's data-availability statement both say the
63 MB Piper voice model is fetched by `tools/fetch_voice.sh` rather than
committed. That is true of the working tree and false of the history: the model
was committed in `0b42d81` and untracked again in `30b10b6`, so the blob is
still reachable and a clone of the published repository would download it.

Three separate problems, not one:

- the paper would state something a reviewer can check and find false
- the repository would redistribute a third-party model the paper says it does
  not redistribute
- every clone pays 63 MB for a file the pipeline downloads anyway

Rewriting history is safe here precisely because there is no remote. It will not
be safe later.

```bash
pip install git-filter-repo
git filter-repo --path corpus/piper_voices --invert-paths
```

`git filter-repo` rewrites the tags as well, so `v1.0.0` and `v1.0.1` survive
with new commit hashes. Nothing outside this repository references those hashes:
the manuscript deliberately resolves the **tag**, not the hash, and says why.

Then confirm the blob is gone and the clone shrank:

```bash
git rev-list --objects --all | grep -i piper_voices || echo "gone"
git count-objects -vH
```

`results/PREFLIGHT.txt` records the commit that was current when it was
generated, so re-run `./run_all.sh` afterwards and commit the refreshed report.

## Then check what a stranger actually gets

The companion paper was returned before review because the submission did not
include a functional repository with a README and documentation. Present files
are not the check; a clean clone that runs is.

```bash
git clone . /tmp/em-audio-clean && cd /tmp/em-audio-clean
./run_all.sh
python3 tools/verify_reproduction.py
```

This has to pass from the clone, not from the working tree, and it is the same
check Daniel's reproduction package exercised.

## Push

```bash
git remote add origin https://github.com/1D-Coda/em-audio.git
git push -u origin main
git push --tags
```

Public, MIT, and **do not rename or move the repository afterwards**. The C2PA
assertion label `io.github.1d-coda.emaudio.evidence` is published in the paper
and cannot be changed, and it is named after this account and repository.

## Commit identity

Every commit is authored as `A. Urias <alex@aurtech.mx>`, which GitHub will
display publicly. That is the same address the manuscript gives for
correspondence, so it is consistent rather than a leak. If you would rather it
not appear, the rewrite above is the moment to change it, since it is the only
time the history can be edited without breaking anyone's clone.

## Repository hygiene before the first push

- `corpus/` and the experiment working directories are gitignored; confirm with
  `git status --short` that nothing generated is staged
- `fixtures/expected/` is regenerated on every run with fresh UUIDs, so it
  dirties the tree on each pipeline run; commit it deliberately, not by reflex
- `results/reference/` is the snapshot an independent reproducer compares
  against, and must match the tag you publish
