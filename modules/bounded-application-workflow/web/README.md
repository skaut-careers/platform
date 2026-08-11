# Skaut Careers Web

Next.js UI for the IT opportunity workflow (M6).

## Stack

- Next.js (App Router) + TypeScript
- Tailwind CSS v4
- CopilotKit (`@copilotkit/react-core`) → FastAPI AG-UI agent (`/copilotkit`)
- Paste CV + job posting → `profile_text` + `job_description_text` → streamed match result
- pnpm, Node 24+

## Run (from module root)

```bash
make install
make dev
```

Open http://127.0.0.1:3000

```bash
make web-dev      # UI only
make web-build    # production build check
make web-typecheck
make web-lint
```
