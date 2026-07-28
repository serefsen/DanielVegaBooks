import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_MODEL   = process.env.OPENROUTER_MODEL || "openai/gpt-4o";
const GITHUB_TOKEN       = process.env.GITHUB_TOKEN;
const REPO_OWNER     = "serefsen";
const REPO_NAME      = "DanielVegaBooks";
const FILE_PATH      = "src/data/posts.js";
const BRANCH         = "main";

const SEED_COUNT = 3;

const TAGS = [
  "Anxiety",
  "Social anxiety",
  "Sleep",
  "Depression",
  "Academic stress",
  "Self-esteem",
  "Communication",
];

function slugify(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60);
}

function readingTime(paragraphs) {
  const words = paragraphs.join(" ").trim().split(/\s+/).length;
  const mins  = Math.max(3, Math.ceil(words / 130));
  return `${mins} min read`;
}

function todayISO() {
  return new Date().toISOString().split("T")[0];
}

function extractExistingPosts(fileContent) {
  const re = /slug:\s*"([^"]+)"[\s\S]*?title:\s*"((?:[^"\\]|\\.)*)"/g;
  const posts = [];
  let m;
  while ((m = re.exec(fileContent)) !== null) {
    posts.push({ slug: m[1], title: JSON.parse(`"${m[2]}"`) });
  }
  return posts;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const ALLOWED_AMAZON_URLS = [
  "https://www.amazon.com/dp/B0H5926917",
  "https://www.amazon.com/dp/B0H5L55D31",
  "https://www.amazon.com/dp/B0H65LW8SN",
];

function resolveAllowedHref(url, validSlugs) {
  if (url === "https://danielvegabooks.com/books/") return url;
  if (ALLOWED_AMAZON_URLS.includes(url)) return url;
  const m = url.match(/^\/blog\/([a-z0-9-]+)\/?$/);
  if (m && validSlugs.includes(m[1])) return `/blog/${m[1]}/`;
  return null;
}

function isExternalHref(href) {
  return /^https?:\/\//.test(href) && !href.startsWith("https://danielvegabooks.com");
}

function linkifyParagraph(raw, validSlugs) {
  const linkRe = /\[([^\]\[]+)\]\(([^()\s]+)\)/g;
  let result = "";
  let lastIndex = 0;
  let m;
  while ((m = linkRe.exec(raw)) !== null) {
    result += escapeHtml(raw.slice(lastIndex, m.index));
    const text = escapeHtml(m[1]);
    const href = resolveAllowedHref(m[2], validSlugs);
    if (href) {
      const attrs = isExternalHref(href) ? ` target="_blank" rel="noopener"` : "";
      result += `<a href="${href}"${attrs}>${text}</a>`;
    } else {
      result += text;
    }
    lastIndex = linkRe.lastIndex;
  }
  result += escapeHtml(raw.slice(lastIndex));
  return result;
}

async function generatePost(topic, existingPosts) {
  const existingPostsList = existingPosts
    .map((p) => `- ${p.title} → /blog/${p.slug}/`)
    .join("\n");

  const systemPrompt = `You write blog posts for a website called DanielVegaBooks.
The site sells CBT-based anxiety workbooks for teenagers. Your audience is parents, school counselors, and teachers — the adults who buy the books and want to help a teenager. Write TO this adult reader, in second person, about their teenager. Never address the teenager directly.

BRAND VOICE RULES:
- Open with a scene an adult reader would recognize from their own life with a teenager — the kitchen table, a closed bedroom door, a phone screen the kid won't look up from, a car ride home from practice. Keep it concrete and specific, never generic or cliché.
- Name and reframe what's going on in plain, warm language — no clinical or textbook framing.
- Walk through ONE practical thing the adult can actually do or say, in everyday language. You may describe a technique in detail, but do not give it a brand name or capitalized title (no "the X Method", no "the Y Tool", no "the Z Wheel").
- Close by connecting, in one natural sentence, to whichever of the three workbooks below best fits this topic, linking to that book's Amazon page. This is a soft mention, not a pitch — no "buy now", no urgency, no promise of guaranteed results.
- Tone: warm, direct, practical, honest. Never preachy. Never promise a fix, a cure, or a guarantee.

EXAMPLE OPENING 1:
"Your kid used to tell you everything on the walk home from school. Lately you get the door closing, the headphones going in before their coat's even off, and a 'fine' that ends the conversation before it starts."

EXAMPLE OPENING 2:
"You're standing in the kitchen when you hear it through the wall — the sharp inhale before a phone call, the pacing, the same sentence rehearsed three times before your kid finally dials the number."

EXAMPLE OPENING 3:
"It's 11 p.m. and the light under their door is still on. You know without asking that they're not doing homework — they're replaying every awkward thing they said today, for the fourth night in a row."

LANGUAGE THAT IS NEVER ALLOWED, in any form:
- "calm down", "just relax", "just breathe", "you've got this", "believe in yourself", "you are enough", "buy now"
- clinical/textbook terms: "disorder", "symptoms", "amygdala", "prefrontal cortex", "diagnosis", "CBT tool" (describe a technique, just don't label it that way)
- any claim of a guaranteed outcome or a miracle fix

BOOKS (pick the ONE that best matches this post's topic, and reference it naturally at the close):
- "Your Alarm Isn't Broken" (https://www.amazon.com/dp/B0H5926917) — panic, 3 a.m. spirals, avoidance, physical anxiety symptoms, sleep
- "Your Awkward Isn't Showing" (https://www.amazon.com/dp/B0H5L55D31) — social anxiety, embarrassment, friendships, feeling watched
- "Your Pressure Isn't Proof" (https://www.amazon.com/dp/B0H65LW8SN) — performance anxiety, tests, perfectionism, fear of letting people down
Link format: [natural phrase mentioning the book or its idea](that book's Amazon URL above) — exactly one such link, near the end of the post, pointing to that specific book's Amazon page.

EXISTING POSTS ON THIS SITE (for internal linking):
${existingPostsList}
If — and only if — one or two of these are genuinely relevant to this topic, link to them naturally inline using [anchor text](/blog/<slug>/) with the exact slug from the list above (note the trailing slash). Do not force a link if none of them truly fit. Never invent a slug that isn't in the list above.

OUTPUT — return ONLY a JSON object with these exact keys:
{
  "title": "string (compelling, 6-10 words, no quotation marks around it)",
  "excerpt": "string (1-2 sentences summarizing the post)",
  "tag": "string (choose exactly one of: ${TAGS.join(", ")})",
  "content": "string (the full post, 700-900 words, paragraphs separated by a blank line / double newline)"
}`;

  const userPrompt = `Write a blog post on this idea: "${topic}"`;

  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${OPENROUTER_API_KEY}`,
      "HTTP-Referer": "https://danielvegabooks.com",
      "X-Title": "Daniel Vega Books",
    },
    body: JSON.stringify({
      model: OPENROUTER_MODEL,
      temperature: 0.7,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user",   content: userPrompt },
      ],
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`OpenRouter error ${res.status}: ${err}`);
  }

  const data = await res.json();
  return JSON.parse(data.choices[0].message.content);
}

async function getFileFromGitHub() {
  const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}?ref=${BRANCH}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`GitHub GET error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const content = Buffer.from(data.content, "base64").toString("utf-8");
  return { content, sha: data.sha };
}

async function putFileToGitHub(newContent, sha, commitMessage) {
  const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${FILE_PATH}`;
  const encoded = Buffer.from(newContent, "utf-8").toString("base64");

  const res = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: commitMessage,
      content: encoded,
      sha,
      branch: BRANCH,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`GitHub PUT error ${res.status}: ${err}`);
  }

  return await res.json();
}

function injectPost(fileContent, post) {
  const insertPoint = fileContent.indexOf("[");
  if (insertPoint === -1) throw new Error("Could not find array opening bracket in posts.js");

  const bodyEntries = post.body
    .map((p) => `      ${JSON.stringify(p)},`)
    .join("\n");

  const postEntry = `
  {
    slug: ${JSON.stringify(post.slug)},
    date: ${JSON.stringify(post.date)},
    readingTime: ${JSON.stringify(post.readingTime)},
    tag: ${JSON.stringify(post.tag)},
    title: ${JSON.stringify(post.title)},
    excerpt: ${JSON.stringify(post.excerpt)},
    body: [
${bodyEntries}
    ],
  },`;

  return (
    fileContent.slice(0, insertPoint + 1) +
    postEntry +
    fileContent.slice(insertPoint + 1)
  );
}

async function main() {
  if (!OPENROUTER_API_KEY) throw new Error("OPENROUTER_API_KEY is not set");
  if (!GITHUB_TOKEN)       throw new Error("GITHUB_TOKEN is not set");

  const topicsPath = path.join(__dirname, "topics.json");
  const topics     = JSON.parse(readFileSync(topicsPath, "utf-8"));
  if (!Array.isArray(topics) || topics.length === 0) {
    throw new Error("topics.json is empty or not an array");
  }

  console.log("Fetching current posts.js from GitHub...");
  const { content: fileContent, sha } = await getFileFromGitHub();

  const totalPosts = (fileContent.match(/^\s{4}slug:\s*/gm) || []).length;
  const index = Math.max(0, totalPosts - SEED_COUNT);

  if (index >= topics.length) {
    console.log(`All ${topics.length} topics have been published. Nothing to do.`);
    return;
  }

  const topic = topics[index];
  console.log(`Topic ${index + 1} of ${topics.length}: ${topic}`);

  const existingPosts = extractExistingPosts(fileContent);
  const validSlugs    = existingPosts.map((p) => p.slug);

  console.log("Calling OpenRouter...");
  const generated = await generatePost(topic, existingPosts);

  const tag     = TAGS.includes(generated.tag) ? generated.tag : "Anxiety";
  const rawBody = String(generated.content)
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean);

  if (rawBody.length === 0) throw new Error("Generated content was empty");

  const postReadingTime = readingTime(rawBody);
  const body = rawBody.map((p) => linkifyParagraph(p, validSlugs));

  const post = {
    slug:        slugify(generated.title),
    date:        todayISO(),
    readingTime: postReadingTime,
    tag,
    title:       generated.title,
    excerpt:     generated.excerpt,
    body,
  };
  console.log(`Generated: "${post.title}" — ${post.tag}, ${post.readingTime}, ${body.length} paragraphs`);

  const updatedContent = injectPost(fileContent, post);

  console.log("Pushing to GitHub via Contents API...");
  const result = await putFileToGitHub(
    updatedContent,
    sha,
    `chore: add post ${index + 1}/${topics.length} — ${post.title}`
  );
  console.log(`Success! Commit: ${result.commit.sha}`);
}

main().catch((err) => {
  console.error("FATAL:", err.message);
  process.exit(1);
});