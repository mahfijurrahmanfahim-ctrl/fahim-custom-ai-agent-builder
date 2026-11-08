import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const location = String(body.location || "").trim().slice(0, 120);
    const category = String(body.category || "restaurants and cafes").trim().slice(0, 120);
    if (!location) return NextResponse.json({ error: "Enter a city or area to search." }, { status: 400 });

    const q = category + " in " + location;
    const enc = encodeURIComponent(q);
    const mapUrl = "https://www.google.com/maps/search/" + enc;
    const searchUrl = "https://www.google.com/search?q=" + enc;
    const instagramUrl = "https://www.google.com/search?q=" + encodeURIComponent("site:instagram.com " + q);
    const facebookUrl = "https://www.google.com/search?q=" + encodeURIComponent("site:facebook.com " + q);
    const answer = [
      "## Free prospect research — " + location,
      "",
      "These are live public-search shortcuts, not a verified list of businesses. Open the links, inspect each business yourself, and only add prospects whose official details you can confirm.",
      "",
      "### Simple prospect checklist",
      "1. Find an independent business with an active public profile.",
      "2. Check its menu, posts or promotions for a genuine design-service fit.",
      "3. Record its official website or public business page and the source you checked.",
      "4. Personalise one short message. Do not assume it needs a redesign.",
      "",
      "Suggested tracker fields: Business | Type | Public website/profile | Specific design opportunity | Source checked | Contacted? | Follow-up date."
    ].join("\n");

    return NextResponse.json({
      answer,
      model: "Free public search links — no API key",
      researchedAt: new Date().toISOString(),
      sources: [
        { url: mapUrl, title: "Find " + category + " on Google Maps" },
        { url: searchUrl, title: "Search public websites for " + category },
        { url: instagramUrl, title: "Find public Instagram business profiles" },
        { url: facebookUrl, title: "Find public Facebook business pages" }
      ]
    });
  } catch {
    return NextResponse.json({ error: "Could not prepare public search links. Please try again." }, { status: 500 });
  }
}
