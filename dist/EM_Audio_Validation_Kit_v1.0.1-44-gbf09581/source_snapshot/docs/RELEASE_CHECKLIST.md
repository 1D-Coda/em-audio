# Cutting a release

The order matters, and two steps are easy to get wrong because they depend on
outputs produced later in the sequence.

1. `./run_all.sh` — must end in `RUN OK`
2. Build the PDFs: `pdflatex` / `bibtex` / `pdflatex` x3 for `manuscript`,
   `supplementary`, `cover_letter`
3. `python3 tools/make_checksums.py` — **again, after the PDFs are built**.
   `run_all.sh` generates the manifest before the documents exist in their
   final form, so a release cut without this step ships a manifest that fails
   on its own PDFs.
4. `python3 tools/freeze_reference.py --tag vX.Y.Z` — deliberately not part of
   `run_all.sh`. If the reference snapshot were refreshed on every run it would
   always match what was just produced and `verify_reproduction.py` would be
   comparing a file against itself.
5. Set `RELEASE` in `tools/verify_reproduction.py` and `version:` in
   `CITATION.cff` to the tag being cut
6. Commit, tag, push the tag, publish the GitHub release
7. Confirm Zenodo archived it and record both DOIs

## Verifying a release before publishing it

The check that matters is not that the files are present but that a stranger
can use them. Extract the tree without `.git` and run the verifier there:

```bash
tar -cf - --exclude=.git --exclude=corpus . | (mkdir -p /tmp/nogit && cd /tmp/nogit && tar -xf -)
python3 /tmp/nogit/tools/verify_reproduction.py
```

It must report that every deterministic output matches. If it instead reports
the whole release as missing, `results/reference/` was not frozen and the tool
fell back to `git show`, which the reader you are serving does not have.
