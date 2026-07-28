import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_MODEL   = process.env.OPENROUTER_MODEL ?? "openai/gpt-4o";
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
"Walk into a room a little late, say the wrong thing in class, trip on a step — and suddenly it feels like a stadium of eyes swung over and locked onto you."

EXAMPLE OPENING 2:
"Right before something that matters — a test, a tryout, raising your hand — your heart starts slamming, your breath goes shallow."

EXAMPLE OPENING 3:
"There's a specific kind of awful that mostly lives at 3 a.m.: lying in the dark while your brain lines up every cringe memory."

OUTPUT — return ONLY a JSON object with these exact keys:
{
  "title": "string (compelling, 6-10 words, no quotation marks around it)",
  "excerpt": "string (1-2 sentences summarizing the post)",
  "tag": "string (choose exactly one of: ${TAGS.join(", ")})",
  "content": "string (the full post, 400-550 words, paragraphs separated by a blank line / double newline)"
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

  console.log("Calling OpenRouter...");
  const generated = await generatePost(topic);

  const tag  = TAGS.includes(generated.tag) ? generated.tag : "Anxiety";
  const body = String(generated.content)
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean);

  if (body.length === 0) throw new Error("Generated content was empty");

  const post = {
    slug:        slugify(generated.title),
    date:        todayISO(),
    readingTime: readingTime(body),
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