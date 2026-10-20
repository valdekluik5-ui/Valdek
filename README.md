# Valdek

Projects built with Claude.

- `quiet-moon/` — Quiet Moon app. Netlify publish directory: `quiet-moon`
- `teleprompter/` — Suffler teleprompter app. Netlify base directory: `teleprompter` (its `netlify.toml` sets the rest)

## Suffler on Netlify

The Moon helper (AI script writing) runs as a Netlify Function at `/api/moon`
(`teleprompter/netlify/functions/moon.mjs`). It calls Claude through Netlify's AI Gateway,
so no API key is stored anywhere; usage comes out of the Netlify account's monthly credits.

1. Site configuration → Build & deploy → Base directory: `teleprompter`.
2. Deploy from Git (drag-and-drop deploys do not include functions).
3. The account must be on a credit-based plan (Free, Personal or Pro) for the AI Gateway.
4. Optional: set the environment variable `MOON_MODEL` (default `claude-opus-5-5`);
   `claude-haiku-5-5` costs far fewer credits per request.

Everything else (teleprompter, captions, filters, music, pause removal, 9:16) runs in the browser.
