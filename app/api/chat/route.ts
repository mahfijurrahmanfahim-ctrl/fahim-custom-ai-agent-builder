import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SYSTEM_PROMPT = [
  "You are FAHIM AUTOPILOT AI, a practical personal business and productivity assistant.",
  "Help Mahfijur Rahman Fahim with graphic design, restaurant menus, social media posts, photo editing, posters, banners, promotional videos, client acquisition and daily work.",
  "Business brand: Fahim Graphic Design. Portfolio: https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/",
  "Fiverr restaurant menu service: https://www.fiverr.com/s/X00EVme",
  "Fiverr social media design service: https://www.fiverr.com/s/qbbQr6y",
  "Be concise, practical and honest. Never invent clients, job openings, contact details, prices, research results or completed actions.",
  "You cannot send emails, messages, contact clients, make purchases or publish content. You may prepare drafts, but always require the owner's explicit approval before any external outreach.",
  "When asked to find clients, do not fabricate leads. Explain when live verified research is unavailable.",
  "Support English and Bengali when requested."
].join("\n");

type ChatMessage = { role?: string; content?: string };

function getMessages(messages: ChatMessage[]) {
  return messages.slice(-20).map((item) => ({
    role: item.role === "assistant" ? "assistant" : "user",
    content: String(item.content || "").slice(0, 12000)
  }));
}

function hermesBaseUrl() {
  const raw = process.env.HERMES_GATEWAY_URL?.trim();
  if (!raw) return null;
  const parsed = new URL(raw);
  if (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && ["localhost", "127.0.0.1"].includes(parsed.hostname))) {
    throw new Error("Hermes gateway URL must use HTTPS (HTTP is allowed only for localhost).");
  }
  return raw.replace(/\/+$/, "").replace(/\/v1$/, "");
}

async function callHermes(messages: ChatMessage[]) {
  const base = hermesBaseUrl();
  const key = process.env.HERMES_API_KEY;
  if (!base || !key) throw new Error("Hermes is not configured");
  const response = await fetch(base + "/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + key
    },
    body: JSON.stringify({
      model: process.env.HERMES_MODEL || "hermes-agent",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        ...getMessages(messages)
      ],
      temperature: 0.7
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(60000)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data?.error?.message || "Hermes gateway request failed (" + response.status + ")");
  const answer = data?.choices?.[0]?.message?.content?.trim();
  if (!answer) throw new Error("Hermes returned an empty response");
  return { answer, model: "Hermes Agent" };
}

async function callGemini(messages: ChatMessage[]) {
  const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!key) throw new Error("Gemini key not configured");
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const contents = getMessages(messages).map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }]
  }));
  const response = await fetch(
    "https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(key),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents,
        generationConfig: { temperature: 0.7, maxOutputTokens: 2048 }
      }),
      cache: "no-store"
    }
  );
  const data = await response.json();
  if (!response.ok) throw new Error("Gemini: " + (data?.error?.message || "request failed"));
  const answer = data?.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text || "").join("").trim();
  if (!answer) throw new Error("Gemini returned an empty response");
  return { answer, model };
}

async function callOpenAICompatible(provider: "groq" | "openrouter", messages: ChatMessage[]) {
  const key = provider === "groq" ? process.env.GROQ_API_KEY : process.env.OPENROUTER_API_KEY;
  if (!key) throw new Error(provider + " key not configured");
  const model = provider === "groq"
    ? (process.env.GROQ_MODEL || "llama-3.3-70b-versatile")
    : (process.env.OPENROUTER_MODEL || "openrouter/auto");
  const endpoint = provider === "groq"
    ? "https://api.groq.com/openai/v1/chat/completions"
    : "https://openrouter.ai/api/v1/chat/completions";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + key,
      ...(provider === "openrouter" ? { "HTTP-Referer": "https://fahim-autopilot-ai.vercel.app", "X-Title": "FAHIM AUTOPILOT AI" } : {})
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        ...getMessages(messages)
      ],
      temperature: 0.7,
      max_tokens: 2048
    }),
    cache: "no-store"
  });
  const data = await response.json();
  if (!response.ok) throw new Error(provider + ": " + (data?.error?.message || "request failed"));
  const answer = data?.choices?.[0]?.message?.content?.trim();
  if (!answer) throw new Error(provider + " returned an empty response");
  return { answer, model: provider + "/" + model };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const messages = Array.isArray(body.messages) ? body.messages as ChatMessage[] : [];
    if (!messages.length) {
      return NextResponse.json({ error: "Please enter a message." }, { status: 400 });
    }

    const failures: string[] = [];
    if (process.env.HERMES_GATEWAY_URL && process.env.HERMES_API_KEY) {
      try {
        return NextResponse.json(await callHermes(messages));
      } catch (error) {
        failures.push("Hermes: " + (error instanceof Error ? error.message : "connection failed"));
      }
    }

    const providers: Array<() => Promise<{ answer: string; model: string }>> = [
      () => callGemini(messages),
      () => callOpenAICompatible("groq", messages),
      () => callOpenAICompatible("openrouter", messages)
    ];
    for (const provider of providers) {
      try {
        return NextResponse.json(await provider());
      } catch (error) {
        failures.push(error instanceof Error ? error.message : "Provider failed");
      }
    }

    const configured = [
      process.env.HERMES_GATEWAY_URL && process.env.HERMES_API_KEY,
      process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY,
      process.env.GROQ_API_KEY,
      process.env.OPENROUTER_API_KEY
    ].some(Boolean);
    return NextResponse.json({
      error: configured
        ? "All configured AI providers failed. Check that your gateway/API keys are active and their free-tier quotas are available. Details: " + failures.join(" | ")
        : "No AI provider is configured yet. Add a fresh GEMINI_API_KEY or GROQ_API_KEY in Vercel Environment Variables, then redeploy. Both can have free usage tiers."
    }, { status: configured ? 502 : 503 });
  } catch (error) {
    return NextResponse.json({
      error: error instanceof Error ? error.message : "Unable to process the request. Please try again."
    }, { status: 500 });
  }
}
