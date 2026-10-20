/* Moon helper: rewrites and writes scripts with Claude.
   Runs on Netlify; the AI Gateway supplies the Anthropic key and address, so there is no key to keep here. */
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const MODEL = process.env.MOON_MODEL || "claude-opus-5-5";
const MAX_TEXT = 8000, MAX_IDEA = 600;

const LANG = { en: "English", uk: "Ukrainian" };

const SYSTEM = `You help a video creator write short scripts she reads aloud to the camera from a teleprompter (Reels, TikTok, YouTube Shorts).
Write the way people talk: short sentences, warm and natural, no hashtags, no emojis, no stage directions, no headings, no quotation marks around the result.
Keep her meaning and her voice. Separate paragraphs with a blank line.
Reply with only the requested text, nothing before or after it.`;

function ask(task, text, lang, idea, avoid) {
  const L = LANG[lang] || "English";
  const other = lang === "uk" ? "English" : "Ukrainian";
  const script = `<script>\n${text}\n</script>`;
  const again = avoid ? `\n\nGive something clearly different from this earlier suggestion:\n<earlier>\n${avoid}\n</earlier>` : "";
  switch (task) {
    case "hook":
      return `${script}\n\nWrite one new opening sentence for this script that makes viewers stop scrolling in the first two seconds. It replaces the current first sentence. Write it in ${L}. Reply with that one sentence only.${again}`;
    case "shorter":
      return `${script}\n\nMake this script about 30% shorter. Keep the opening, the main points and the closing call to action. Write it in ${L}.${again}`;
    case "warmer":
      return `${script}\n\nRewrite this script in a warmer, more personal tone, like talking to a close friend. Keep the length about the same. Write it in ${L}.${again}`;
    case "translate":
      return `${script}\n\nTranslate this script into natural spoken ${other}. Keep the paragraphs.${again}`;
    case "fix":
      return `${script}\n\nFix spelling, grammar and awkward phrases in this script. Change as little as possible. Keep it in its language.${again}`;
    case "write":
      return `Write a script of about 120 to 180 words in ${L} for a short vertical video about: ${idea}\n\nStart with a strong first sentence, give two or three concrete points, end with a short friendly call to action.` +
        (text.trim() ? `\n\nHere is her current script, to match her style:\n${script}` : "") + again;
  }
  return null;
}

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

async function create(params) {
  try {
    /* if a request is declined, Anthropic retries it on its recommended fallback model */
    return await client.beta.messages.create({ ...params, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default" });
  } catch (e) {
    if (e instanceof Anthropic.BadRequestError) return await client.messages.create(params); /* gateway without the fallback beta */
    throw e;
  }
}

export default async (req) => {
  if (req.method !== "POST") return json({ error: "method" }, 405);
  /* only the app's own pages may use the helper */
  const origin = req.headers.get("origin");
  if (origin && new URL(origin).host !== new URL(req.url).host) return json({ error: "origin" }, 403);

  let body;
  try { body = await req.json(); } catch { return json({ error: "bad request" }, 400); }
  const text = String(body.text || "").slice(0, MAX_TEXT);
  const idea = String(body.idea || "").slice(0, MAX_IDEA).trim();
  const avoid = String(body.avoid || "").slice(0, MAX_TEXT);
  if (body.task === "write" ? !idea : !text.trim()) return json({ error: "empty" }, 400);
  const prompt = ask(body.task, text, body.lang, idea, avoid);
  if (!prompt) return json({ error: "task" }, 400);

  try {
    const res = await create({
      model: MODEL,
      max_tokens: 8000,
      output_config: { effort: "low" },
      system: SYSTEM,
      messages: [{ role: "user", content: prompt }],
    });
    if (res.stop_reason === "refusal") return json({ error: "refused" }, 422);
    const out = res.content.filter((b) => b.type === "text").map((b) => b.text).join("").trim();
    if (!out) return json({ error: "empty answer" }, 502);
    return json({ text: out });
  } catch (e) {
    if (e instanceof Anthropic.RateLimitError) return json({ error: "busy" }, 429);
    if (e instanceof Anthropic.AuthenticationError || e instanceof Anthropic.PermissionDeniedError) return json({ error: "no AI access" }, 503);
    if (e instanceof Anthropic.APIError) return json({ error: `AI error ${e.status ?? ""}`.trim() }, 502);
    return json({ error: "AI unreachable" }, 502);
  }
};

export const config = {
  path: "/api/moon",
  /* keeps one visitor from using up the monthly AI credits */
  rateLimit: { windowLimit: 20, windowSize: 60, aggregateBy: ["ip", "domain"] },
};
