import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SYSTEM_PROMPT = [
  "You are FAHIM AUTOPILOT AI, a practical personal business and productivity assistant.",
  "Help the owner Mahfijur Rahman Fahim with graphic design, restaurant menus, social media posts, photo editing, posters, banners, promotional videos, client acquisition and daily work.",
  "Business brand: Fahim Graphic Design. Portfolio: https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/",
  "Fiverr restaurant menu service: https://www.fiverr.com/s/X00EVme",
  "Fiverr social media design service: https://www.fiverr.com/s/qbbQr6y",
  "Be concise, practical and honest. Never invent clients, job openings, contact details, prices, research results or completed actions.",
  "You cannot send emails, messages, contact clients, make purchases or publish content. You may prepare drafts, but always require the owner's explicit approval before any external outreach.",
  "When asked to find clients, explain that verified live lead research needs a connected search source; do not fabricate leads.",
  "Use clear step-by-step instructions for technical tasks. Support English and Bengali when requested."
].join("\n");

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const messages = Array.isArray(body.messages) ? body.messages : [];
    if (!messages.length) {
      return NextResponse.json({ error: "Please enter a message." }, { status: 400 });
    }
    const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      return NextResponse.json({
        error: "Gemini API key is not configured. Add GEMINI_API_KEY in Vercel → Settings → Environment Variables, then redeploy."
      }, { status: 503 });
    }

    const contents = messages.slice(-20).map((item: { role?: string; content?: string }) => ({
      role: item.role === "assistant" ? "model" : "user",
      parts: [{ text: String(item.content || "").slice(0, 12000) }]
    }));

    const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
    const response = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(apiKey),
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
    if (!response.ok) {
      const detail = data?.error?.message || "Gemini request failed.";
      return NextResponse.json({ error: detail }, { status: response.status });
    }
    const answer = data?.candidates?.[0]?.content?.parts
      ?.map((part: { text?: string }) => part.text || "")
      .join("")
      .trim();

    if (!answer) {
      return NextResponse.json({ error: "The AI provider returned an empty response." }, { status: 502 });
    }
    return NextResponse.json({ answer, model });
  } catch {
    return NextResponse.json({ error: "Unable to process the request. Please try again." }, { status: 500 });
  }
}
