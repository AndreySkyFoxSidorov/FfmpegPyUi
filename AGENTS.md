# Code Writing Guidelines

## Core Principles

- Prefer simple, direct, readable code.
- Prefer explicit code over elegant architecture.
- Keep code small and easy to understand.
- Do not create abstractions for cleanliness or symmetry alone.
- Keep logic close to the place where it executes.
- Code should be easy to read from top to bottom.
- Avoid deep nesting.
- Avoid over-separating UI, validation, formatting, and state update logic when that makes the code fragmented.
- Prefer 2-5 duplicated lines of clear code over a tiny helper with no real value.

## Classes And Methods

- Keep methods compact.
- As a rough guideline, aim for 5-9 methods per class unless there is a clear reason to have more.
- Add a new method only for:
  - a large block of logic;
  - reused logic;
  - a clear business action;
  - a separate step that genuinely improves readability.
- Do not extract these into separate methods:
  - simple null checks;
  - simple bool checks;
  - one-line wrappers;
  - UI toggle helpers;
  - tiny formatting helpers;
  - simple getters;
  - save/load wrappers;
  - trivial conversions;
  - one-use logic that is easier to read in place.
- Do not create generic helper classes or utility layers without a real repeated need.
- Do not add enterprise-style structure, manager layers, or large architectural constructs without direct need.

## Conditions And Control Flow

- Use direct `if` / `if/else` statements at the call site.
- Do not create one-use condition helpers for simple conditions.
- Do not use `switch` in any form:
  - `switch` statement;
  - `switch` expression;
  - pattern switch;
  - switch-like operator.
- Use early returns only for:
  - errors;
  - blockers;
  - invalid input;
  - invalid state.
- Do not use early returns for the normal success path.
- Keep the normal execution path linear and readable.
- Avoid deep nesting. If nesting grows because of invalid state handling, prefer a guard check near the start.

## Comments And Text Files

- Write code comments in English.
- Comments should explain non-obvious decisions, constraints, or important context.
- Do not add comments that only repeat what the code already says.
- Store project text files as UTF-8.
- If a touched text file is ANSI/Windows-1252, convert it to UTF-8 before editing content.
- Do not leave new or edited text files as ANSI/Windows-1252.

## File Editing

- If the user asks to change files, change the files directly instead of only describing a plan.
- If the user explicitly asks for code text, provide the complete code for the requested file or class.
- Do not invent success.
- If required access, permission, authentication, or tool capability is missing:
  - stop the operation;
  - report the exact blocker;
  - wait for the user's decision.
- Do not continue write operations when access is read-only or unavailable.
- Do not revert changes made by someone else unless explicitly asked.
- If a file already has unfamiliar changes, work with those changes instead of discarding them.

## Contract Synchronization

This rule is useful for any project where one API, bridge, or command contract is duplicated across several languages, SDKs, or transport layers.

- Treat all implementations of the same external contract as one contract surface.
- If a command contract, payload, field, type, enum-like value, timestamp format, error code, security rule, or processing rule changes in one place, review and sync every matching implementation in the same task.
- If externally observable behavior changes, also update:
  - test panels or test harnesses;
  - API documentation;
  - HTML/Markdown documentation;
  - integration examples.
- Do not allow intentional divergence unless the user explicitly asks for it.
- If synchronization is blocked, stop, name the unsynced surface, and wait for the user's decision.
- A contract-related task is complete only after all relevant wrappers, SDKs, bridges, and follow-up surfaces have been reviewed.

## Search And Local Tools

- Prefer repo-local tools over global binaries.
- For search, use repo-local `rg` first when available.
- If repo-local `rg` cannot run because of OS/CPU mismatch, report that clearly and use a fallback search.


