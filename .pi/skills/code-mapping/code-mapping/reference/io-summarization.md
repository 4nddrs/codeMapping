# I/O summarization rules

Goal: keep artifacts small and readable while preserving **scientific usefulness**.

## Scalars and small structures

- Keep bools, ints, short strings, small dicts.
- Round floats to ~6 significant digits unless domain needs more.
- Preserve NaN/Inf as strings if JSON cannot hold them.

## NumPy / tensor-like arrays

Emit an object, not a full nested list:

```json
{
  "_ndarray": true,
  "shape": [512, 800, 3],
  "dtype": "uint8",
  "min": 0.0,
  "max": 255.0,
  "mean": 132.35,
  "first8": [202.0, 199.0, 193.0, 202.0, 199.0, 193.0, 202.0, 199.0]
}
```

Optional enrichments:

- `empty: true` if size 0
- `centroid` for Nx2/Nx3 point-like data
- `nonzero` / `nonzero_frac` / `unique` for masks
- `note: "RGB image"` when obvious
- `path` to the asset file under the run directory

If `size <= 24`, you may also include full `values`.

## Long numeric lists

If length > ~12:

```json
{ "_list": true, "len": 631, "min": 0.0, "max": 1.0, "first": [/* up to 8 */] }
```

## Long lists of dicts (poses, cameras, candidates)

Keep `len`, fully summarize `first` (and optionally `second`), drop the rest with an explicit ellipsis note.

## Nested tool traces

Preserve structure (`name`, `args` summary, `result` summary, `duration`) but apply the same array rules recursively.

## Assets

Prefer:

```json
"assets": {
  "rgb": "node_data/target_sg.perceive/assets/rgb.png",
  "mask": "…",
  "cloud": "…"
}
```

Do not base64 giant blobs into the mapping JSON.

## Forbidden

- API keys, cookies, `.env` bodies
- Home-directory absolute paths that embed usernames **with** credentials (relative repo paths preferred)
- Claiming a summary field is “the full array”
