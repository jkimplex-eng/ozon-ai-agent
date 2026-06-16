# Skills System

## Purpose

The project uses a file-based Skills system under [C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\skills](C:\Users\user\Documents\Codex\2026-05-13\github\ozon-ai-agent\skills) so new capabilities can be attached without changing the core decision, approval, or learning modules.

## Skill Structure

Each skill lives in its own folder and must contain:

- `SKILL.md`
- `rules.md`
- `examples.md`

Example:

```text
skills/
  analyst/
    SKILL.md
    rules.md
    examples.md
```

## How To Create A Skill

1. Add the skill directory under `skills/`.
2. Create `SKILL.md`, `rules.md`, and `examples.md`.
3. Add the skill name to `skills/index.yaml`.
4. Run `ozon-agent skills reload`.
5. Validate with `ozon-agent skills list` and `ozon-agent skills show <name>`.

## How To Connect A Skill

The loader reads `skills/index.yaml` on agent startup and validates each listed skill directory.

- Environment variables are not required.
- Registration is automatic through the skill loader and registry.
- Invalid structure raises a loader error instead of silently skipping a broken skill.

## How To Disable A Skill

1. Remove the skill name from `skills/index.yaml`, or
2. Delete or archive the skill directory, then
3. Run `ozon-agent skills reload`

If a listed skill is missing required files, reload fails fast so the broken state is visible.

## CLI

- `ozon-agent skills list`
- `ozon-agent skills show analyst`
- `ozon-agent skills reload`

## Future Integrations

The infrastructure is prepared for future skill-backed integrations such as:

- `mcp-ozon-seller`
- `Firecrawl`
- `ozon-seller-api-skill`

These integrations are not implemented yet. The current system provides the registry, loader, validation, and CLI surface only.
