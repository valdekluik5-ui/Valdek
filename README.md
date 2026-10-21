# Valdek

Projects built with Claude.

- `quiet-moon/` — Quiet Moon app. Netlify publish directory: `quiet-moon`
- `teleprompter/` — Suffler teleprompter app. Netlify base directory: `teleprompter` (its `netlify.toml` sets the rest)

- `suffler/` — Suffler v18, the next version (in progress). Moon helper uses Google Gemini with the user's own
  free key (stored only on that phone) and an "Ask ChatGPT instead" copy-and-paste backup; no server needed.
  Meant for GitHub Pages: `https://valdekluik5-ui.github.io/Valdek/suffler/`

## Suffler v17 on Netlify (prototype)

The Moon helper (AI script writing) runs as a Netlify Function at `/api/moon`
(`teleprompter/netlify/functions/moon.mjs`). It calls Claude through Netlify's AI Gateway,
so no API key is stored anywhere; usage comes out of the Netlify account's monthly credits.

1. Site configuration → Build & deploy → Base directory: `teleprompter`.
2. Deploy from Git (drag-and-drop deploys do not include functions).
3. The account must be on a credit-based plan (Free, Personal or Pro) for the AI Gateway.
4. Optional: set the environment variable `MOON_MODEL` (default `claude-opus-5-5`);
   `claude-haiku-5-5` costs far fewer credits per request.

Everything else (teleprompter, captions, filters, music, pause removal, 9:16) runs in the browser.
