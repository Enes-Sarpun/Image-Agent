# TODOS

Items deferred from Sprint 1 engineering review.

## Packaging

- [ ] Resolve `image_agent` package namespace: either rename `src/` → `image_agent/` (cleaner for `pip install -e .`) or verify that `pyproject.toml`'s `package-dir = {"image_agent" = "src"}` works end-to-end with `image-agent` CLI entry point.

## Batch CLI

- [ ] Add `--workers N` flag to `src/main.py` batch mode for parallel processing.
- [ ] Add `--output <path>` flag to control output file location.
- [ ] Add JSONL output format alongside existing CSV + JSON.

## Content Validation

- [ ] Replace `PIL.Image.verify()` with a two-open pattern (verify → re-open for dimensions) or investigate if there is a single-open approach that avoids the PIL verify+reopen quirk cleanly.
- [ ] Add per-analyzer timeout enforcement so a hung LLM call cannot block the FastAPI worker indefinitely (document max latency in README in the meantime).
