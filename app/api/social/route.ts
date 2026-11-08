import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const platform = String(body.platform || "Instagram and Facebook").slice(0, 80);
    const goal = String(body.goal || "Build brand awareness").slice(0, 160);
    const topic = String(body.topic || "").trim().slice(0, 500);
    const tone = String(body.tone || "Professional and friendly").slice(0, 120);
    if (!topic) return NextResponse.json({ error: "Enter a post topic first." }, { status: 400 });

    const portfolio = "https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/";
    const menuGig = "https://www.fiverr.com/s/X00EVme";
    const socialGig = "https://www.fiverr.com/s/qbbQr6y";
    const answer = [
      "## Campaign angle",
      topic + " — a clear showcase of the service and the value of polished visual communication.",
      "",
      "## Opening hook",
      "Make your business stand out with visuals that feel unmistakably yours.",
      "",
      "## Caption draft",
      "Your brand deserves more than an ordinary post.\n\nAt Fahim Graphic Design, I create thoughtful visuals for businesses — from " + topic.toLowerCase() + " to promotional graphics and branded content.\n\nLooking for a fresh creative direction? Explore my work and get in touch.",
      "",
      "## Call to action",
      "View the portfolio: " + portfolio,
      "",
      "## Hashtags",
      "#FahimGraphicDesign #GraphicDesign #BusinessDesign #SocialMediaDesign #CreativeStudio #PortugalBusiness #BrandVisuals",
      "",
      "## Visual direction",
      "Premium black-and-gold palette; one strong focal image; clean hierarchy; generous spacing; readable typography. Keep the design focused on one message.",
      "",
      "## Suggested on-image text",
      topic + "\nCreative Design. Professional Results.",
      "",
      "## Alt text",
      "Promotional graphic presenting " + topic + " by Fahim Graphic Design.",
      "",
      "## Story version",
      "Need standout visuals for your business? Explore Fahim Graphic Design.\n" + portfolio,
      "",
      "## Publishing notes",
      "Platform: " + platform + " | Goal: " + goal + " | Brand voice: " + tone,
      "Review the wording and replace any generic line with a real project detail before publishing. No post has been scheduled or published.",
      "",
      "Service links: Menu design " + menuGig + " | Social media design " + socialGig
    ].join("\n");

    return NextResponse.json({ answer, model: "Free built-in content template — no API key", createdAt: new Date().toISOString() });
  } catch {
    return NextResponse.json({ error: "Could not create the social post template." }, { status: 500 });
  }
}
