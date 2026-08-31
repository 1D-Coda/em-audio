# Publishing the repository and depositing the archive

**Order: GitHub, then Zenodo, then the journal.** Zenodo archives a GitHub
release, so the repository has to exist first. An earlier draft of this file
proposed reserving a DOI before creating the repository, to keep the deposit
identifier out of the signed manifests. That was solving a problem worth not
having, and it is simpler to not put a DOI in the manifests at all.

## Why the schema URI is not the DOI

The `schema` field of the assertion ends up inside every signed manifest and
every frozen fixture, so whatever it says has to be settled before the last
pipeline run. Making it a DOI would mean the deposit must exist before the
fixtures are built, and the deposit needs the repository, and the repository
needs the fixtures.

It does not need to be a DOI. What a schema identifier has to do is resolve, and
not depend on a registration that can lapse. The repository URL does both, and
the Zenodo archive preserves the content even if the repository disappears. The
DOIs belong in the paper's data and code availability statements, which is prose
and can be edited without regenerating anything.

`SCHEMA` in `em_audio/manifest_schema.py` is therefore already final:

    https://github.com/1D-Coda/em-audio/blob/main/docs/em-audio-schema-1.0.md

The one obligation this creates is that `docs/em-audio-schema-1.0.md` must exist
in the repository before it goes public, or the URI 404s exactly the way the old
one did.

## Sequence

**1. Clean the history and publish the repository.** See `PUBLISH_REPO.md`. The
voice model has to come out of the history first, and a clean clone has to run
end to end before the push.

**2. Tag and release.** Run the pipeline one final time so `results/PREFLIGHT.txt`
records the released state, commit, tag, push the tag, and cut a GitHub release.

**3. Connect Zenodo.** Log into Zenodo with the GitHub account, open the GitHub
tab, switch the repository on, then cut the release. Zenodo archives it and
mints two identifiers:

- the **version DOI**, pointing at that exact release
- the **concept DOI**, always resolving to the newest version

Cite the concept DOI where the paper refers to the artefact in general, and the
version DOI where it refers to the evaluated state.

**4. Put the URL and the DOIs in the paper.** Data availability and Code
availability currently say the URL is supplied with the submission. Replace that
text. The journal's research-data Option C is a requirement, not a suggestion:
the data must be deposited, cited and linked in the article at submission.

**5. Refresh the reference snapshot.** `results/reference/` is what an
independent reproducer compares against, and `RELEASE` in
`tools/verify_reproduction.py` names the tag those files came from. Both must
name the tag you published.

**6. Submit.**

## What not to do

Do not rename or move the repository afterwards. The assertion label
`io.github.1d-coda.emaudio.evidence` is published in the paper and cannot be
changed, and the schema URI is inside signed manifests.

Do not deposit only the code. The deposit is the whole tagged tree, including
`results/machine_readable/`, `results/reference/` and `results/independent/`,
since those are what the paper's claims are checked against.
