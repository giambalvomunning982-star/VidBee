# Contributing to VidBee

Thank you for taking the time to improve VidBee. These notes keep the project maintainable and easy to review.

## Getting Ready
- Use Node.js 18+ and pnpm 8+.
- Install dependencies with `pnpm install`.
- Run `pnpm dev` to test changes locally.

## Tech Stack
- Runtime: Electron 38, electron-vite, electron-builder.
- Frontend: React 19, React Router, Jotai, React Hook Form, Tailwind CSS 4, shadcn/ui, Lucide icons.
- Tooling: TypeScript 5, pnpm, Biome, dayjs, electron-log, electron-store, electron-updater, i18next, next-themes.

## Local Development
- Use `pnpm install` to pull dependencies after cloning.
- Start the Electron and Vite development environment with `pnpm dev`; hot module replacement is already configured.
- Preview the production build locally with `pnpm start`.

## Useful Scripts

| Command | Purpose |
| --- | --- |
| `pnpm run typecheck` | Type-check the main and renderer projects. |
| `pnpm build` | Run type checks and produce production bundles. |
| `pnpm build:win` / `pnpm build:mac` / `pnpm build:linux` | Create platform-specific distributables. |
| `pnpm build:unpack` | Produce unpacked output directories for inspection. |
| `pnpm run check` | Run lint, format, type, and i18n checks. |
| `pnpm run fix` | Auto-fix fixable lint issues locally. |

## Development Guidelines

### Code Formatting

- Run `pnpm run fix` before committing to auto-fix formatable issues.
- Run `pnpm run check` locally to verify all checks pass before pushing.
- The project uses [Biome](https://biomejs.dev/) (via `ultracite` preset) for linting and formatting.
- **Attribute sorting is disabled** to prevent CI deadlocks. You may order HTML/JSX attributes in any logical order (recommended: semantic grouping like `id`, `className`, `data-*`, event handlers, other props).

### Pre-commit Hooks

- A Husky pre-commit hook runs lightweight checks on staged files only.
- The hook does NOT auto-modify files; it only validates to avoid unexpected changes.

## Project Structure

```text
apps/desktop/src/
|-- main/            # Electron main process, IPC services, configuration
|-- preload/         # Context bridge and preload helpers
`-- renderer/
    |-- src/
    |   |-- pages/      # Application routes (Home, Settings, Playlist, etc.)
    |   |-- components/ # UI components, download views, shared controls
    |   |-- data/       # Static datasets such as popularSites.ts
    |   |-- hooks/      # Custom hooks and global atoms
    |   |-- lib/        # Utilities shared across the renderer
    |   `-- assets/     # Global styles and icons
    `-- index.html
```

## Internationalization
- i18next drives localization with English (`en`) and Simplified Chinese (`zh-CN`) namespaces.
- Only update strings in `apps/desktop/src/renderer/src/locales/en.json`; maintainers handle the other locales.
- Keep copy edits focused and avoid removing translation keys without discussion.

## Configuration and Storage
- Persistent settings are stored with `electron-store` and exposed through IPC helpers.
- User-facing preferences such as download paths and themes live in `apps/desktop/src/main/settings.ts` and related services.
- Logs are recorded with `electron-log` to simplify troubleshooting.

## Packaging
- Build production bundles with `pnpm build`.
- Create platform-specific artifacts with `pnpm build:win`, `pnpm build:mac`, or `pnpm build:linux`.
- Use `pnpm build:unpack` to generate unpacked directories under `apps/desktop/dist/` for manual inspection.
- Bundle `yt-dlp` under `apps/desktop/resources/` and `ffmpeg/ffprobe` under `apps/desktop/resources/ffmpeg/` before packaging so merges and audio extraction work out of the box.

## Working on Changes
- Keep each pull request focused on a single problem or feature.
- Run `pnpm run check` before committing to ensure all validations pass.
- Write comments and console messages in English only.
- When updating copy in the app, adjust strings in `apps/desktop/src/renderer/src/locales/en.json`; other locale files are handled by maintainers.

## CI/CD Pipeline

### Read-Only Check Mode

The CI pipeline uses a **read-only check** approach. This means:

- **CI only validates, never modifies files.** The `ultracite check` command runs in `--write=false` mode.
- **No more formatting deadlocks.** Previous configurations caused CI to fail when attribute ordering differed, then the pre-commit hook would reformat, creating an infinite loop. This is now resolved.
- **Each check step is independent.** Lint, type-check, and i18n checks run as separate steps, so failures are easy to identify.

### What Happens in CI

1. `pnpm install` — Install dependencies
2. `ultracite check --write=false` — Read-only lint/format validation
3. `tsc --noEmit` — TypeScript type checking
4. `check-locales.js` — i18n consistency check
5. Build artifacts are produced

If any step fails, CI reports exactly which step failed with full output for debugging.

## Troubleshooting CI Errors

If your PR fails CI checks, follow these steps to reproduce and fix locally:

### 1. Run the full check suite

```bash
pnpm run check
```

This runs the same checks as CI: lint, type-check, and i18n validation.

### 2. Fix lint/format issues

```bash
pnpm run fix
```

This auto-fixes all fixable issues. Then run `pnpm run check` again to verify.

### 3. Fix TypeScript errors

```bash
pnpm run typecheck
```

Address any type errors reported. Common causes:
- Missing imports
- Type mismatches
- Unused variables

### 4. Fix i18n issues

```bash
pnpm run check:i18n
```

Ensure all translation keys used in code exist in `en.json`.

### 5. Verify before pushing

```bash
pnpm run check
# If any errors, run:
pnpm run fix
# Then check again:
pnpm run check
```

### Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `useSortedAttributes` | Attribute ordering | Attribute sorting is now disabled. Order attributes logically. |
| `ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL` | Sub-package check failure | Run `pnpm --filter ./apps/desktop run check` directly for detailed output |
| Type errors in CI | TypeScript mismatches | Run `pnpm run typecheck` locally and fix reported issues |

## Opening Issues
- Search existing issues to avoid duplicates.
- Describe the problem clearly with steps to reproduce, expected behaviour, and screenshots or logs when useful.

## Submitting Pull Requests
- Explain the motivation and impact of the change in the description.
- Mention any user facing updates or migrations.
- Confirm that `pnpm run check` passes and note any follow-up work that is out of scope.

We appreciate every contribution that keeps VidBee simple and reliable.
