# ADR-0001: Preserve observations, bound requests, and require run logs

- **Status:** Accepted
- **Date:** 2026-10-11
- **Decision owners:** Project owner, with AI collaborator review
- **Supersedes:** None
- **Superseded by:** None

## Context

The bounded loop repeatedly submits all completed tool interactions. Four tool
attempts limit execution but can still return large files. The owner requested
detailed logs and deterministic selection of useful model-context fields.
Current tool fields mostly are the evidence, and file reading has no range API.

## Decision

Retain complete chronological observations for now. Do not summarize or remove
content silently. Bound the complete Ollama JSON request body at a configurable
64 KiB default and return non-retryable `context_limit_reached` before network
access when exceeded. The exact boundary belongs in the adapter because it owns
the wire encoding. The byte budget does not promise token-window compatibility.

Require `logs_dir` from the trusted harness caller. Create a separate UUID-named
JSONL log for every run; reject destinations inside the target repository.
Flush records before continuing and stop with `logging_failed` on understood
filesystem failures. The owner explicitly chose mandatory logging. Preserve
original unexpected exceptions even when interruption logging also fails.

## Options and rationale

- Model summaries add probabilistic selection and an extra model interaction.
- Dropping older observations loses evidence already paid for and may force
  repeated calls within a small tool budget.
- File excerpts can hide evidence that the existing reader cannot selectively
  retrieve. These alternatives need an observed investigation-quality problem.
- Continuing after a logging failure breaks the agreed record contract.

The selected approach keeps the mechanics inspectable and supplies a measured
baseline before adding context-management abstractions or full tracing.

## Consequences

Large results can terminate an investigation, and trusted log configuration is
now required. Logs contain full accepted repository observations and can grow;
they are ignored by Git and are not model-accessible memory. I/O failures can
leave incomplete records. Flush is not an `fsync` guarantee. Token configuration,
log retention, richer tracing, and recovery from oversized context remain
future work when concrete needs justify them.

## Validation

Deterministic boundary, logging, failure, and cross-component tests pass. The
repeatable example measures encoded request growth from 1,642 to 2,749 bytes
over three tool interactions without a live model. See the Block 3.4 workbook
for test results, exact contracts, and known limitations.
