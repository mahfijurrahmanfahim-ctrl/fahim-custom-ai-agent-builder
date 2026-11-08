import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

type GroundingChunk = { web?: { uri?: string; title?: string } };

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const location = String(body.location || "").trim().slice(0, 120);
    const category = String(body.category || "restaurants and cafes").trim().slice(0, 120);
    const count = Math.min(8, Math.max(3, Number(body.count) || 5));

    if (!location) {
      return NextResponse.json({ error: "Enter a city or area to search." }, { status: 400 });
    }

    const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
    if (!key) {
      return NextResponse.json({
        error: "Live lead research needs GEMINI_API_KEY in Vercel Environment Variables. Add the key there and redeploy."
      }, { status: 503 });
    }

    const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
    const prompt = [
      "Act as a careful public-business research assistant for Fahim Graphic Design, a freelance graphic design service offering restaurant menus, social media graphics, promotional posters and branded visuals.",
      "Research " + count + " real " + category + " businesses in " + location + ".",
      "Prioritise independent businesses that could reasonably benefit from menu redesign, social media visuals, posters or promotional design.",
      "Use Google Search grounding. Only include businesses supported by a real public source. Never invent a business, website, address, owner, email, phone number, weakness or design need.",
      "For each candidate provide: business name; business type; city/area; one concrete, publicly verifiable reason it may be a relevant prospect (or say 'design opportunity not confirmed'); official website or public business profile if found; and a suggested non-pushy design service.",
      "Do not infer that a business has poor design unless the source visibly supports it. Do not provide private personal contact information. Do not write or send outreach.",
      "If fewer than " + count + " candidates can be verified, return fewer rather than padding.",
      "Format as a concise numbered list. Clearly distinguish verified facts from suggestions."
    ].join("\n");

    const response = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(key),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          tools: [{ google_search: {} }],
          generationConfig: { temperature: 0.2, maxOutputTokens: 3000 }
        }),
        cache: "no-store"
      }
    );

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json({
        error: "Lead research provider error: " + (data?.error?.message || "request failed")
      }, { status: response.status });
    }

    const candidate = data?.candidates?.[0];
    const answer = candidate?.content?.parts?.map((part: { text?: string }) => part.text || "").join("").trim();
    if (!answer) {
      return NextResponse.json({ error: "The research provider returned no usable results. Try another location or category." }, { status: 502 });
    }

    const chunks: GroundingChunk[] = candidate?.groundingMetadata?.groundingChunks || [];
    const sources = chunks
      .map((chunk) => chunk.web)
      .filter((web): web is { uri: string; title?: string } => Boolean(web?.uri))
      .map((web) => ({ url: web.uri, title: web.title || web.uri }))
      .filter((source, index, all) => all.findIndex((item) => item.url === source.url) === index)
      .slice(0, 12);

    return NextResponse.json({ answer, sources, model, researchedAt: new Date().toISOString() });
  } catch {
    return NextResponse.json({ error: "Could not complete lead research. Please try again." }, { status: 500 });
  }
}
