import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SYSTEM = [
  "You are the senior social media strategist and copywriter for Fahim Graphic Design, a freelance design studio.",
  "Services: restaurant menu design, social media graphics, promotional posters, photo editing and branded visuals.",
  "Portfolio: https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/",
  "Fiverr menu gig: https://www.fiverr.com/s/X00EVme",
  "Fiverr social design gig: https://www.fiverr.com/s/qbbQr6y",
  "Create polished, natural, platform-appropriate content. Avoid generic hype, spammy hashtags, fake testimonials, invented discounts, invented client results or unsupported claims.",
  "Return: campaign angle; 1 strong opening hook; caption with clear line breaks; one clear CTA; 5-10 relevant hashtags; visual/design brief; suggested on-image text; accessibility alt text; best posting-time guidance phrased as a test suggestion, not a guaranteed optimal time; and a short story version.",
  "For design service promotion, direct people to the portfolio or relevant Fiverr gig. Do not claim a post is scheduled or published.",
  "Be concise and ready to copy. Output in clean Markdown."
].join("\n");

async function runGemini(prompt: string) {
  const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!key) throw new Error("Gemini key not configured");
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(key), {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ systemInstruction: { parts: [{ text: SYSTEM }] }, contents: [{ role: "user", parts: [{ text: prompt }] }], generationConfig: { temperature: 0.75, maxOutputTokens: 2200 } }), cache: "no-store"
  });
  const data = await response.json();
  if (!response.ok) throw new Error("Gemini: " + (data?.error?.message || "request failed"));
  const answer = data?.candidates?.[0]?.content?.parts?.map((p: {text?: string}) => p.text || "").join("").trim();
  if (!answer) throw new Error("Gemini returned no content");
  return { answer, model };
}

async function runCompatible(provider: "groq" | "openrouter", prompt: string) {
  const key = provider === "groq" ? process.env.GROQ_API_KEY : process.env.OPENROUTER_API_KEY;
  if (!key) throw new Error(provider + " key not configured");
  const model = provider === "groq" ? (process.env.GROQ_MODEL || "llama-3.3-70b-versatile") : (process.env.OPENROUTER_MODEL || "openrouter/auto");
  const endpoint = provider === "groq" ? "https://api.groq.com/openai/v1/chat/completions" : "https://openrouter.ai/api/v1/chat/completions";
  const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + key }, body: JSON.stringify({ model, messages: [{ role: "system", content: SYSTEM }, { role: "user", content: prompt }], temperature: 0.75, max_tokens: 2200 }), cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(provider + ": " + (data?.error?.message || "request failed"));
  const answer = data?.choices?.[0]?.message?.content?.trim();
  if (!answer) throw new Error(provider + " returned no content");
  return { answer, model: provider + "/" + model };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const platform = String(body.platform || "Instagram and Facebook").slice(0, 80);
    const goal = String(body.goal || "Build brand awareness").slice(0, 160);
    const topic = String(body.topic || "").trim().slice(0, 500);
    const tone = String(body.tone || "Professional and friendly").slice(0, 120);
    if (!topic) return NextResponse.json({ error: "Enter a post topic first." }, { status: 400 });
    const prompt = "Create one complete social media post package. Platform(s): " + platform + ". Goal: " + goal + ". Topic/offer: " + topic + ". Brand voice: " + tone + ". Audience: independent businesses and potential design clients in Portugal and the UK. Use natural English suitable for an international audience. Never invent facts, prices, client names, results or deadlines.";
    const providers = [() => runGemini(prompt), () => runCompatible("groq", prompt), () => runCompatible("openrouter", prompt)];
    const failures: string[] = [];
    for (const provider of providers) {
      try { const result = await provider(); return NextResponse.json({ ...result, createdAt: new Date().toISOString() }); }
      catch (error) { failures.push(error instanceof Error ? error.message : "Provider failed"); }
    }
    return NextResponse.json({ error: "All configured AI providers failed. Check Vercel environment variables and provider quotas. " + failures.join(" | ") }, { status: 502 });
  } catch {
    return NextResponse.json({ error: "Could not create social content. Please try again." }, { status: 500 });
  }
}
