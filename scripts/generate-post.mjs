import { readFileSync, writeFileSync } from "fs";
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

// ── Config ──────────────────────────────────────────────────────────────────
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const GITHUB_TOKEN   = process.env.GITHUB_TOKEN;        // Actions provides this automatically
const REPO_OWNER     = "serefsen";
const REPO_NAME      = "DanielVegaBooks";
const FILE_PATH      = "src/data/posts.js";             // path inside the repo
const BRANCH         = "main";

// ── Helpers ──────────────────────────────────────────────────────────────────
function slugify(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60);
}

function readingTime(text) {
  const words = text.trim().split(/\s+/).length;
  return Math.max(3, Math.ceil(words / 130));
}

function todayISO() {
  return new Date().toISOString().split("T")[0];
}

// ── Topic selection ──────────────────────────────────────────────────────────
function pickTopic(topics, existingPosts) {
  const usedTitles = new Set(existingPosts.map((p) => p.title?.toLowerCase()));
  const unused = topics.filter((t) => !usedTitles.has(t.topic.toLowerCase()));
  const pool   = unused.length > 0 ? unused : topics;
  return pool[Math.floor(Math.random() * pool.length)];
}

// ── OpenAI call ──────────────────────────────────────────────────────────────
async function generatePost(topic) {
  const systemPrompt = `You write blog posts for a website called DanielVegaBooks. 
The site sells CBT workbooks for teenagers. Your audience is parents, school counselors, and teachers.

BRAND VOICE RULES:
- Open with a scene (a moment a parent or counselor would recognize)
- Name and reframe the anxiety without clinical jargon
- Explain ONE concrete CBT tool clearly
- Close softly — no hard sell
- Tone: warm, direct, practical. Never preachy.

EXAMPLE OPENING 1:
"It's 11 PM and your teenager is still awake, heart pounding, convinced they'll blank on tomorrow's exam. Sound familiar?"

EXAMPLE OPENING 2:
"She walked into the cafeteria, scanned the room for a friendly face, and turned around. Again."

EXAMPLE OPENING 3:
"He knew the answer. He just couldn't make himself raise his hand."

FORMAT: Return ONLY a JSON object — no markdown fences, no preamble — with these exact keys:
{
  "title": "string (compelling, 6-10 words, SEO-friendly for parents searching teen anxiety help)",
  "excerpt": "string (2 sentences, what the post covers)",
  "content": "string (full post, 400-550 words, plain text paragraphs separated by \\n\\n)"
}`;

  const userPrompt = `Write a blog post about: ${topic.topic}
SEO keywords to naturally include: ${topic.keywords || topic.topic}`;

  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4o",
      temperature: 0.7,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user",   content: userPrompt },
      ],
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`OpenAI error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const raw  = data.choices[0].message.content.trim();

  // Strip accidental markdown fences
  const clean = raw.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  return JSON.parse(clean);
}

// ── GitHub Contents API ───────────────────────────────────────────────────────
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

// ── Parse existing posts array from posts.js ──────────────────────────────────
function parseExistingPosts(fileContent) {
  // Extract the array literal from:  export const posts = [ ... ];
  const match = fileContent.match(/export\s+const\s+posts\s*=\s*(\[[\s\S]*\])\s*;?\s*$/);
  if (!match) throw new Error("Could not find posts array in posts.js");
  // eslint-disable-next-line no-eval
  return eval(match[1]); // safe: we control this file
}

// ── Inject new post into file content ────────────────────────────────────────
function injectPost(fileContent, newPost) {
  // Find the opening bracket of the array and insert after it
  const insertPoint = fileContent.indexOf("[");
  if (insertPoint === -1) throw new Error("Could not find array opening bracket in posts.js");

  const postEntry = `
  {
    id: "${newPost.id}",
    title: ${JSON.stringify(newPost.title)},
    slug: "${newPost.slug}",
    date: "${newPost.date}",
    excerpt: ${JSON.stringify(newPost.excerpt)},
    readingTime: ${newPost.readingTime},
    content: ${JSON.stringify(newPost.content)},
  },`;

  return (
    fileContent.slice(0, insertPoint + 1) +
    postEntry +
    fileContent.slice(insertPoint + 1)
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  if (!OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not set");
  if (!GITHUB_TOKEN)   throw new Error("GITHUB_TOKEN is not set");

  // 1. Load topics
  const topicsPath = path.join(__dirname, "topics.json");
  const topics     = JSON.parse(readFileSync(topicsPath, "utf-8"));

  // 2. Fetch current posts.js from GitHub (gets latest SHA — no stale clone issues)
  console.log("Fetching current posts.js from GitHub...");
  const { content: fileContent, sha } = await getFileFromGitHub();

  // 3. Parse existing posts to avoid topic repetition
  const existingPosts = parseExistingPosts(fileContent);
  console.log(`Found ${existingPosts.length} existing posts.`);

  // 4. Pick a topic
  const topic = pickTopic(topics, existingPosts);
  console.log(`Selected topic: ${topic.topic}`);

  // 5. Generate post via OpenAI
  console.log("Calling OpenAI...");
  const generated = await generatePost(topic);

  // 6. Build post object
  const slug = slugify(generated.title);
  const id   = `post-${Date.now()}`;
  const newPost = {
    id,
    title:       generated.title,
    slug,
    date:        todayISO(),
    excerpt:     generated.excerpt,
    readingTime: readingTime(generated.content),
    content:     generated.content,
  };
  console.log(`Generated: "${newPost.title}" (${newPost.readingTime} min read)`);

  // 7. Inject into file content
  const updatedContent = injectPost(fileContent, newPost);

  // 8. Push via GitHub Contents API (no git, no fast-forward conflicts)
  console.log("Pushing to GitHub via Contents API...");
  const result = await putFileToGitHub(
    updatedContent,
    sha,
    `chore: add post — ${newPost.title}`
  );
  console.log(`Success! Commit: ${result.commit.sha}`);
}

main().catch((err) => {
  console.error("FATAL:", err.message);
  process.exit(1);
});
