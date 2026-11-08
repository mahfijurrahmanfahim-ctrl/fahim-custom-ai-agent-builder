import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const focus = String(body.focus || "restaurant and cafe design").slice(0, 160);
    const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
    if (!key) return NextResponse.json({ error: "Add GEMINI_API_KEY to Vercel Environment Variables to generate project concepts." }, { status: 503 });

    const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
    const prompt = [
      "You are the creative director for Fahim Graphic Design, a freelance studio offering restaurant menus, social media design, photo editing, posters, banners and promotional videos.",
      "Create exactly 3 original portfolio-ready design project briefs focused on: " + focus + ".",
      "Make the projects commercially realistic, visually distinctive and achievable by one freelance designer using Canva and AI-assisted creative tools.",
      "For each project provide: project title; target business/client type; business objective; deliverables (specific count and formats); art direction (palette, typography mood, composition, photography); exact production checklist; and a short portfolio case-study caption.",
      "Do not invent real clients, claim the work has been commissioned, or fabricate business facts. Label all concepts as self-initiated portfolio projects. Do not invent restaurant menu items, prices, addresses, logos or contact details.",
      "Return clean markdown with clear headings. Make each brief detailed enough to start creating immediately."
    ].join("\n");

    const response = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(key),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.85, maxOutputTokens: 3500 }
        }),
        cache: "no-store"
      }
    );
    const data = await response.json();
    if (!response.ok) return NextResponse.json({ error: "Project generator error: " + (data?.error?.message || "request failed") }, { status: response.status });
    const answer = data?.candidates?.[0]?.content?.parts?.map((part: { text?: string }) => part.text || "").join("").trim();
    if (!answer) return NextResponse.json({ error: "No project concepts were returned. Try again." }, { status: 502 });
    return NextResponse.json({ answer, model, createdAt: new Date().toISOString() });
  } catch {
    return NextResponse.json({ error: "Could not generate project briefs. Please try again." }, { status: 500 });
  }
}
