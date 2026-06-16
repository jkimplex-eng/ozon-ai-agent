# ozon_api rules

- Treat API contracts as authoritative.
- Use local swagger.json as the source of truth for endpoint discovery.
- Preserve idempotent reads and explicit pagination behavior.
- Resolve endpoint meaning from path, tags, and schemas before proposing client code.
- Do not introduce write calls without separate approval.
