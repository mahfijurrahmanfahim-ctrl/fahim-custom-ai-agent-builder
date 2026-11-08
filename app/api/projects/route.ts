import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SYSTEM = "You are the creative director for Fahim Graphic Design, a freelance studio offering restaurant menus, social media design, photo editing, posters, banners and promotional videos. Create original, commercially realistic portfolio concepts achievable by one designer using Canva and AI-assisted creative tools. Label every concept self-initiated; never pretend it is a commissioned client project. Never invent menu items, prices, addresses, logos or contact details.";

async function generateWithGemini(prompt: string) {
  const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!key) throw new Error("Gemini key not configured");
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(key), {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ systemInstruction: { parts: [{ text: SYSTEM }] }, contents: [{ role: "user", parts: [{ text: prompt }] }], generationConfig: { temperature: 0.85, maxOutputTokens: 3500 } }), cache: "no-store"
  });
  const data = await response.json();
  if (!response.ok) throw new Error("Gemini: " + (data?.error?.message || "request failed"));
  const answer = data?.candidates?.[0]?.content?.parts?.map((p: {text?: string}) => p.text || "").join("").trim();
  if (!answer) throw new Error("Gemini returned no content");
  return { answer, model };
}

async function generateOpenAI(provider: "groq" | "openrouter", prompt: string) {
  const key = provider === "groq" ? process.env.GROQ_API_KEY : process.env.OPENROUTER_API_KEY;
  if (!key) throw new Error(provider + " key not configured");
  const model = provider === "groq" ? (process.env.GROQ_MODEL || "llama-3.3-70b-versatile") : (process.env.OPENROUTER_MODEL || "openrouter/auto");
  const endpoint = provider === "groq" ? "https://api.groq.com/openai/v1/chat/completions" : "https://openrouter.ai/api/v1/chat/completions";
  const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + key }, body: JSON.stringify({ model, messages: [{ role: "system", content: SYSTEM }, { role: "user", content: prompt }], temperature: 0.85, max_tokens: 3500 }), cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(provider + ": " + (data?.error?.message || "request failed"));
  const answer = data?.choices?.[0]?.message?.content?.trim();
  if (!answer) throw new Error(provider + " returned no content");
  return { answer, model: provider + "/" + model };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const focus = String(body.focus || "restaurant and cafe design").slice(0, 160);
    const prompt = [
      "Create exactly 3 original portfolio-ready design project briefs focused on: " + focus + ".",
      "For each project provide: title; target business/client type; objective; deliverables with specific counts and formats; art direction (palette, typography mood, composition, photography); exact production checklist; and a short portfolio case-study caption.",
      "Make each brief detailed enough to start creating immediately. Include realistic constraints and a distinct creative angle.",
      "Return clean markdown with clear headings."
    ].join("\n");
    const providers = [
      () => generateWithGemini(prompt),
      () => generateOpenAI("groq", prompt),
      () => generateOpenAI("openrouter", prompt)
    ];
    const failures: string[] = [];
    for (const provider of providers) {
      try {
        const result = await provider();
        return NextResponse.json({ ...result, createdAt: new Date().toISOString() });
      } catch (error) {
        failures.push(error instanceof Error ? error.message : "Provider failed");
      }
    }
    return NextResponse.json({ error: "All configured AI providers failed. Check your Vercel API keys and available quotas. " + failures.join(" | ") }, { status: 502 });
  } catch {
    return NextResponse.json({ error: "Could not generate project briefs. Please try again." }, { status: 500 });
  }
}
