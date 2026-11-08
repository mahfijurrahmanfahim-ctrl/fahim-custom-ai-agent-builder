import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const focus = String(body.focus || "restaurant and cafe design").slice(0, 160);
    const answer = [
      "## 1. Signature brand campaign",
      "**Focus:** " + focus + "\n**Objective:** Create a cohesive visual identity campaign for a fictional concept brand, clearly labelled as a self-initiated portfolio project.\n**Deliverables:** 1 hero poster, 3 social posts, 3 story frames and 1 profile cover.\n**Art direction:** Premium black-and-gold palette, strong product photography, clean modern typography and consistent spacing.\n**Checklist:** Define a fictional brand name; create a simple visual system; design each format; check mobile legibility; export web-ready files.\n**Case-study note:** Self-initiated visual campaign exploring a consistent brand system across social formats.",
      "",
      "## 2. Promotional offer layout system",
      "**Focus:** " + focus + "\n**Objective:** Show how one campaign idea adapts to multiple placements without changing the core message.\n**Deliverables:** 1 A4 poster, 1 square post, 1 portrait post and 1 story.\n**Art direction:** One focal image, bold headline, restrained supporting copy and a clear CTA.\n**Checklist:** Write placeholder copy; establish hierarchy; adapt layouts; test contrast; export PNG and PDF. Do not invent real prices, offers or business details.\n**Case-study note:** Self-initiated layout study demonstrating flexible promotional design.",
      "",
      "## 3. Social content mini-series",
      "**Focus:** " + focus + "\n**Objective:** Build a recognisable 5-post series that makes a service or product easy to understand.\n**Deliverables:** 5 carousel or single-image posts, 5 captions and 5 matching story covers.\n**Art direction:** Consistent grid, typography pairing, repeatable colour palette and varied imagery.\n**Checklist:** Choose one audience; assign one message per post; design a reusable template; proofread; export and organise source files.\n**Case-study note:** Self-initiated content series focused on clarity, consistency and brand recognition.",
      "",
      "**Portfolio honesty:** These are practice concepts, not commissioned client work. Use fictional brands or supplied real assets with permission. Never present them as paid client projects."
    ].join("\n");

    return NextResponse.json({ answer, model: "Free built-in project templates — no API key", createdAt: new Date().toISOString() });
  } catch {
    return NextResponse.json({ error: "Could not prepare project brief templates." }, { status: 500 });
  }
}
