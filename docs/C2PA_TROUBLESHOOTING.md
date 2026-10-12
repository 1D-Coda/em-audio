# C2PA signing and composition: troubleshooting

These are the failures we hit while wiring the signed transport. Each one
produces an error that does not name its cause.

## Signing key format

`c2patool` needs the signing key in PKCS#8 form and as PEM content, not as a
path. A SEC1 key or a file path produces a decoder error that does not mention
the key format.

## `c2pa.opened` and the `parentOf` ingredient

A hand-written `c2pa.opened` action without an `ingredients` parameter is
rejected with `assertion.action.ingredientMismatch`. The specification requires
the action to carry a hashed-URI reference to the `parentOf` ingredient
assertion. Let the claim generator insert it instead of writing it by hand.

## Ingredient manifests in compositions

`c2patool` resolves `ResourceRef` identifiers relative to the directory of the
manifest-definition file. An ingredient's stored `manifest_data.c2pa` must be
referenced by a path relative to that directory. An absolute path is reported
as `resource not found` even when the file exists. On Windows the path must use
forward slashes.

## `c2pa.placed` and `componentOf` ingredients

A `c2pa.placed` action must carry a hashed-URI reference to its `componentOf`
ingredient assertion (C2PA 2.4, section 18.16.3). The reference cannot be written
by hand before signing. Give the action an `ingredientIds` parameter naming the
ingredient's `instance_id`; the claim generator resolves it to the hashed URI at
signing time.
