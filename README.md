# Valdek

Projects built with Claude.

- `quiet-moon/` — Quiet Moon app. Netlify publish directory: `quiet-moon`
- `teleprompter/` — Suffler teleprompter app.

## Suffler hosting

GitHub Pages (free): repository Settings → Pages → Deploy from a branch → `main`, folder `/ (root)`.
The app is then at `https://valdekluik5-ui.github.io/Valdek/teleprompter/`.
It also still works on Netlify with Base directory `teleprompter`.

Moon helper calls Google Gemini straight from the phone with the user's own free key
(made at https://aistudio.google.com/apikey, pasted once in the app, stored only on that phone).
"Ask ChatGPT instead" copies the request, opens ChatGPT, and takes the answer back by paste.
