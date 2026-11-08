"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity, ArrowUp, Bot, BriefcaseBusiness, Check, ChevronDown, Clock3,
  Command, FileText, Globe2, Image as ImageIcon, Menu, MessageSquare,
  MoreHorizontal, Plus, Search, Send, Settings2, ShieldCheck, Sparkles,
  SquarePen, Trash2, WandSparkles, X
} from "lucide-react";

type Message = { role: "user" | "assistant"; content: string };
type Draft = { id: string; title: string; body: string; createdAt: string };
type LeadResearch = { answer: string; sources: { url: string; title: string }[]; model: string; researchedAt: string };
type ProjectResult = { answer: string; model: string; createdAt: string };
type SocialResult = { answer: string; model: string; createdAt: string };

const starters = [
  { icon: BriefcaseBusiness, title: "Find potential clients", prompt: "Help me create a practical plan to find verified restaurant and small-business clients for my graphic design services. Do not invent leads." },
  { icon: WandSparkles, title: "Create a client message", prompt: "Draft a short, professional outreach message introducing my graphic design services. Keep it ready for my approval; do not send it." },
  { icon: FileText, title: "Improve my portfolio", prompt: "Review the positioning of my graphic design portfolio and suggest the highest-impact improvements." },
  { icon: ImageIcon, title: "Plan a design project", prompt: "Help me plan a premium black-and-gold promotional design for a business client." }
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState("Assistant");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [notice, setNotice] = useState("");
  const [leadLocation, setLeadLocation] = useState("Lisbon, Portugal");
  const [leadCategory, setLeadCategory] = useState("restaurants and cafes");
  const [leadResearch, setLeadResearch] = useState<LeadResearch | null>(null);
  const [leadBusy, setLeadBusy] = useState(false);
  const [leadError, setLeadError] = useState("");
  const [projectFocus, setProjectFocus] = useState("restaurant and cafe design");
  const [projectResult, setProjectResult] = useState<ProjectResult | null>(null);
  const [projectBusy, setProjectBusy] = useState(false);
  const [projectError, setProjectError] = useState("");
  const [socialPlatform, setSocialPlatform] = useState("Instagram and Facebook");
  const [socialGoal, setSocialGoal] = useState("Attract new design clients");
  const [socialTopic, setSocialTopic] = useState("Restaurant menu design");
  const [socialTone, setSocialTone] = useState("Premium, confident and friendly");
  const [socialResult, setSocialResult] = useState<SocialResult | null>(null);
  const [socialBusy, setSocialBusy] = useState(false);
  const [socialError, setSocialError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("fahim-autopilot-messages");
      const savedDrafts = localStorage.getItem("fahim-autopilot-drafts");
      if (saved) setMessages(JSON.parse(saved));
      if (savedDrafts) setDrafts(JSON.parse(savedDrafts));
    } catch {}
  }, []);

  useEffect(() => {
    localStorage.setItem("fahim-autopilot-messages", JSON.stringify(messages));
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    localStorage.setItem("fahim-autopilot-drafts", JSON.stringify(drafts));
  }, [drafts]);

  async function sendMessage(text?: string) {
    const value = (text ?? input).trim();
    if (!value || busy) return;
    const next = [...messages, { role: "user" as const, content: value }];
    setMessages(next);
    setInput("");
    setBusy(true);
    setNotice("");
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "The request failed.");
      setMessages([...next, { role: "assistant", content: data.answer }]);
    } catch (error) {
      setMessages([...next, { role: "assistant", content: "I couldn't complete that request. " + (error instanceof Error ? error.message : "Please try again.") }]);
    } finally {
      setBusy(false);
    }
  }

  async function findLeads() {
    if (!leadLocation.trim() || leadBusy) return;
    setLeadBusy(true); setLeadError(""); setLeadResearch(null);
    try {
      const response = await fetch("/api/leads", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ location: leadLocation, category: leadCategory, count: 5 }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Lead research failed.");
      setLeadResearch(data);
    } catch (error) { setLeadError(error instanceof Error ? error.message : "Lead research failed."); }
    finally { setLeadBusy(false); }
  }

  async function generateProjects() {
    if (projectBusy) return;
    setProjectBusy(true); setProjectError(""); setProjectResult(null);
    try {
      const response = await fetch("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ focus: projectFocus }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Project generation failed.");
      setProjectResult(data);
    } catch (error) { setProjectError(error instanceof Error ? error.message : "Project generation failed."); }
    finally { setProjectBusy(false); }
  }

  async function createSocialContent() {\n    if (socialBusy || !socialTopic.trim()) return;\n    setSocialBusy(true); setSocialError(""); setSocialResult(null);\n    try {\n      const response = await fetch("/api/social", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ platform: socialPlatform, goal: socialGoal, topic: socialTopic, tone: socialTone }) });\n      const data = await response.json();\n      if (!response.ok) throw new Error(data.error || "Social content generation failed.");\n      setSocialResult(data);\n    } catch (error) { setSocialError(error instanceof Error ? error.message : "Social content generation failed."); }\n    finally { setSocialBusy(false); }\n  }\n\n  function saveSocialDraft() {\n    if (!socialResult) return;\n    setDrafts([{ id: String(Date.now()), title: "Social media post — " + socialTopic, body: socialResult.answer, createdAt: new Date().toLocaleString() }, ...drafts]);\n    setNotice("Social content saved for your approval. Nothing has been published.");\n    setActive("Approval Queue");\n  }\n\n  function saveProject() {
    if (!projectResult) return;
    setDrafts([{ id: String(Date.now()), title: "Portfolio project concepts", body: projectResult.answer, createdAt: new Date().toLocaleString() }, ...drafts]);
    setNotice("Project briefs saved to your workspace. Nothing has been published.");
    setActive("Approval Queue");
  }

  function saveDraft() {
    const last = [...messages].reverse().find((m) => m.role === "assistant");
    if (!last) return;
    setDrafts([{ id: String(Date.now()), title: "Outreach draft", body: last.content, createdAt: new Date().toLocaleString() }, ...drafts]);
    setNotice("Saved to your approval queue. Nothing has been sent.");
    setActive("Approval Queue");
  }

  function clearChat() {
    setMessages([]);
    setNotice("Chat cleared.");
  }

  const nav = [
    { label: "Assistant", icon: MessageSquare },
    { label: "Client Finder", icon: Search },
    { label: "Social Media Manager", icon: WandSparkles },\n    { label: "Content Studio", icon: ImageIcon },
    { label: "Approval Queue", icon: ShieldCheck }
  ];

  return (
    <main className="app-shell">
      <aside className={"sidebar " + (sidebarOpen ? "sidebar-open" : "")}>
        <div className="brand">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <div><div className="brand-name">FAHIM <span>AUTOPILOT</span></div><div className="brand-sub">PERSONAL AI WORKSPACE</div></div>
          <button className="icon-btn mobile-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={18}/></button>
        </div>
        <button className="new-chat" onClick={clearChat}><SquarePen size={16}/> New conversation <Plus size={15}/></button>
        <div className="nav-label">WORKSPACE</div>
        <nav className="nav-list">
          {nav.map(({label, icon: Icon}) => (
            <button key={label} className={"nav-item " + (active === label ? "active" : "")} onClick={() => {setActive(label); setSidebarOpen(false);}}>
              <Icon size={17}/><span>{label}</span>{label === "Approval Queue" && drafts.length > 0 && <span className="nav-count">{drafts.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-spacer"/>
        <div className="safety-card"><div className="safety-icon"><ShieldCheck size={16}/></div><div><strong>You stay in control</strong><p>Client messages need your approval before sending.</p></div></div>
        <div className="profile">
          <div className="avatar">F</div><div className="profile-info"><strong>Fahim</strong><span>Personal workspace</span></div><MoreHorizontal size={18} className="muted"/>
        </div>
      </aside>

      {sidebarOpen && <button className="scrim" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"/>}

      <section className="main-panel">
        <header className="topbar">
          <div className="top-left"><button className="icon-btn menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={19}/></button><span className="breadcrumb">Workspace</span><span className="crumb-slash">/</span><strong>{active}</strong></div>
          <div className="top-right"><span className="status-dot"/><span className="status-text">Private workspace</span><button className="icon-btn" title="Settings"><Settings2 size={18}/></button></div>
        </header>

        <div className="content-area">
          {active === "Assistant" && (
            <div className="chat-wrap">
              <div className="welcome-block">
                <div className="eyebrow"><span className="eyebrow-line"/> YOUR BUSINESS, ONE STEP AHEAD</div>
                <h1>Good to see you.<br/><span>What are we building today?</span></h1>
                <p>Your personal AI partner for ideas, clients, creative work and getting things done.</p>
              </div>
              {messages.length === 0 && <div className="starter-grid">{starters.map(({icon: Icon, title, prompt}) => <button className="starter-card" key={title} onClick={() => sendMessage(prompt)}><span className="starter-icon"><Icon size={18}/></span><span>{title}</span><ArrowUp size={15} className="starter-arrow"/></button>)}</div>}
              <div className="messages">
                {messages.map((message, index) => <div className={"message-row " + message.role} key={index}><div className="message-avatar">{message.role === "assistant" ? <Sparkles size={15}/> : "F"}</div><div className="message-body"><div className="message-name">{message.role === "assistant" ? "FAHIM AUTOPILOT" : "YOU"}</div><div className="message-text">{message.content}</div>{message.role === "assistant" && <button className="save-draft" onClick={saveDraft}><ShieldCheck size={14}/> Save response to approval queue</button>}</div></div>)}
                {busy && <div className="message-row assistant"><div className="message-avatar"><Sparkles size={15}/></div><div className="message-body"><div className="message-name">FAHIM AUTOPILOT</div><div className="typing"><i/><i/><i/> Thinking through it…</div></div></div>}
                <div ref={endRef}/>
              </div>
              <div className="composer-wrap"><div className="composer"><textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => {if(e.key === "Enter" && !e.shiftKey){e.preventDefault();sendMessage();}}} placeholder="Ask FAHIM AUTOPILOT anything…" rows={1}/><div className="composer-bottom"><span><Command size={12}/> Enter to send · Shift + Enter for new line</span><button className="send-btn" onClick={() => sendMessage()} disabled={!input.trim() || busy} aria-label="Send message"><ArrowUp size={18}/></button></div></div><div className="composer-note"><ShieldCheck size={12}/> Your conversations stay in this browser. External actions always require your approval.</div></div>
            </div>
          )}

          {active === "Client Finder" && <div className="page-section"><div className="eyebrow"><span className="eyebrow-line"/> GROW YOUR BUSINESS</div><h1>Find your next <span>great client.</span></h1><p className="section-lead">Research real public businesses and identify relevant design opportunities. Every result must have a source; nothing is contacted automatically.</p><div className="feature-panel"><div className="feature-icon"><Globe2 size={22}/></div><div className="lead-form"><h3>Live business research</h3><label htmlFor="lead-location">City or area</label><input id="lead-location" value={leadLocation} onChange={(e)=>setLeadLocation(e.target.value)} placeholder="e.g. Lisbon, Portugal"/><label htmlFor="lead-category">Business type</label><select id="lead-category" value={leadCategory} onChange={(e)=>setLeadCategory(e.target.value)}><option value="restaurants and cafes">Restaurants & cafes</option><option value="gyms and fitness studios">Gyms & fitness studios</option><option value="clothing boutiques and fashion brands">Clothing & fashion</option><option value="beauty salons and barbershops">Beauty & barbershops</option><option value="hotels and guest houses">Hotels & guest houses</option><option value="small local businesses">Small local businesses</option></select><button className="primary-btn" onClick={findLeads} disabled={leadBusy || !leadLocation.trim()}>{leadBusy ? "Researching public sources…" : "Find real business leads"} <Search size={15}/></button><p className="lead-disclaimer">Uses Google Search grounding through your configured Gemini API key. Results are research leads, not guaranteed buyers. Review every source before contacting a business.</p></div></div>{leadError && <div className="error-panel">{leadError}</div>}{leadResearch && <div className="lead-results"><div className="results-heading"><div><h3>Research results</h3><span>Checked {new Date(leadResearch.researchedAt).toLocaleString()} · {leadResearch.model}</span></div><button className="secondary-btn" onClick={()=>{setMessages([...messages,{role:"user",content:"Turn this sourced business research into a shortlist with personalised, approval-only outreach drafts. Do not send anything.\n\n"+leadResearch.answer}]);setActive("Assistant");}}>Prepare outreach drafts</button></div><pre className="lead-answer">{leadResearch.answer}</pre>{leadResearch.sources.length>0 && <div className="source-list"><strong>Research sources</strong>{leadResearch.sources.map((source,i)=><a key={source.url} href={source.url} target="_blank" rel="noreferrer">{i+1}. {source.title} ↗</a>)}</div>}</div>}<div className="info-grid"><div className="info-tile"><Search size={18}/><strong>Public-source research</strong><span>Only use businesses supported by searchable public sources.</span></div><div className="info-tile"><Check size={18}/><strong>Verify before outreach</strong><span>Check the official website and business details yourself.</span></div><div className="info-tile"><ShieldCheck size={18}/><strong>You approve every message</strong><span>No emails or DMs are sent by this research tool.</span></div></div></div>}

          {active === "Social Media Manager" && <div className="page-section"><div className="eyebrow"><span className="eyebrow-line"/> SOCIAL MEDIA COMMAND CENTRE</div><h1>Your social media, <span>managed smarter.</span></h1><p className="section-lead">Plan campaigns, write platform-ready captions, create hashtag sets and build a consistent posting routine for Fahim Graphic Design. Every post stays a draft until you approve it.</p><div className="feature-panel"><div className="feature-icon"><WandSparkles size={22}/></div><div className="lead-form"><h3>AI social content creator</h3><label htmlFor="social-platform">Platforms</label><select id="social-platform" value={socialPlatform} onChange={e=>setSocialPlatform(e.target.value)}><option>Instagram and Facebook</option><option>Instagram</option><option>Facebook</option><option>LinkedIn</option><option>TikTok</option></select><label htmlFor="social-goal">Campaign goal</label><select id="social-goal" value={socialGoal} onChange={e=>setSocialGoal(e.target.value)}><option>Attract new design clients</option><option>Promote restaurant menu design</option><option>Promote social media design service</option><option>Showcase photo editing work</option><option>Build brand awareness</option><option>Promote a Fiverr gig</option></select><label htmlFor="social-topic">Post topic or offer</label><input id="social-topic" value={socialTopic} onChange={e=>setSocialTopic(e.target.value)} placeholder="What should this post promote?"/><label htmlFor="social-tone">Brand voice</label><select id="social-tone" value={socialTone} onChange={e=>setSocialTone(e.target.value)}><option>Premium, confident and friendly</option><option>Luxury black-and-gold, bold</option><option>Creative, energetic and modern</option><option>Simple, professional and trustworthy</option></select><button className="primary-btn" onClick={createSocialContent} disabled={socialBusy || !socialTopic.trim()}>{socialBusy ? "Creating your campaign…" : "Create social media post"} <WandSparkles size={15}/></button><p className="lead-disclaimer">Creates caption, hook, call to action, hashtags, visual direction and posting suggestions. It does not publish or contact anyone.</p></div></div>{socialError && <div className="error-panel">{socialError}</div>}{socialResult && <div className="lead-results"><div className="results-heading"><div><h3>Your social media draft</h3><span>Created {new Date(socialResult.createdAt).toLocaleString()} · {socialResult.model}</span></div><button className="secondary-btn" onClick={saveSocialDraft}>Save to approval queue</button></div><pre className="lead-answer">{socialResult.answer}</pre><div className="draft-actions"><button className="secondary-btn" onClick={()=>navigator.clipboard.writeText(socialResult.answer).then(()=>setNotice("Social media draft copied. It has not been published."))}>Copy draft</button><button className="secondary-btn" onClick={createSocialContent}>Regenerate</button></div></div>}<div className="info-grid"><div className="info-tile"><FileText size={18}/><strong>Platform-ready copy</strong><span>Hooks, captions, calls to action and relevant hashtags.</span></div><div className="info-tile"><ImageIcon size={18}/><strong>Creative direction</strong><span>Visual concept, layout, image guidance and on-image text.</span></div><div className="info-tile"><ShieldCheck size={18}/><strong>Approval first</strong><span>Nothing gets published without your explicit approval.</span></div></div></div>}

          {active === "Content Studio" && <div className="page-section"><div className="eyebrow"><span className="eyebrow-line"/> CREATIVE WORKSPACE</div><h1>Make something <span>stand out.</span></h1><p className="section-lead">Generate practical, self-initiated portfolio projects with production-ready creative direction.</p><div className="feature-panel"><div className="feature-icon"><WandSparkles size={22}/></div><div className="lead-form"><h3>AI portfolio project builder</h3><label htmlFor="project-focus">Project direction</label><select id="project-focus" value={projectFocus} onChange={(e)=>setProjectFocus(e.target.value)}><option value="restaurant and cafe design">Restaurant & cafe design</option><option value="luxury food and beverage product advertising">Luxury food & beverage advertising</option><option value="gym and fitness brand campaigns">Gym & fitness campaigns</option><option value="clothing and fashion brand visuals">Fashion & clothing brand visuals</option><option value="beauty salon and barbershop branding">Beauty & barbershop branding</option><option value="social media content for small businesses">Small business social media</option><option value="photo editing and premium product visuals">Photo editing & product visuals</option><option value="short-form promotional video concepts">Promotional video concepts</option></select><button className="primary-btn" onClick={generateProjects} disabled={projectBusy}>{projectBusy ? "Building project briefs…" : "Generate 3 new projects"} <WandSparkles size={15}/></button><p className="lead-disclaimer">Creates self-initiated portfolio concepts, not fake client commissions. No work is published automatically.</p></div></div>{projectError && <div className="error-panel">{projectError}</div>}{projectResult && <div className="lead-results"><div className="results-heading"><div><h3>Your new project briefs</h3><span>Generated {new Date(projectResult.createdAt).toLocaleString()} · {projectResult.model}</span></div><button className="secondary-btn" onClick={saveProject}>Save project briefs</button></div><pre className="lead-answer">{projectResult.answer}</pre><div className="draft-actions"><button className="secondary-btn" onClick={()=>navigator.clipboard.writeText(projectResult.answer).then(()=>setNotice("Project briefs copied."))}>Copy all briefs</button><button className="secondary-btn" onClick={generateProjects}>Generate another set</button></div></div>}<div className="studio-grid">{[{title:"Restaurant menu",desc:"Build a clean menu using real supplied items and prices.",prompt:"Create a professional restaurant menu design brief. Ask me for the actual menu items, prices and brand details; never invent them.",icon:FileText},{title:"Social media campaign",desc:"Develop a campaign with clear visual direction.",prompt:"Create a social media campaign concept for Fahim Graphic Design, including visual direction, caption and call to action.",icon:ImageIcon},{title:"Promotional video",desc:"Create a cinematic short-form video plan.",prompt:"Create a cinematic 30-second promotional video concept for Fahim Graphic Design with scene-by-scene visuals and voiceover.",icon:Activity},{title:"Client proposal",desc:"Prepare a clear proposal for a potential client.",prompt:"Create a professional graphic design service proposal template for a small business client. Leave unknown client details as placeholders.",icon:BriefcaseBusiness}].map(({title,desc,prompt,icon:Icon})=><button className="studio-card" key={title} onClick={()=>{setActive("Assistant");sendMessage(prompt);}}><span className="studio-icon"><Icon size={19}/></span><strong>{title}</strong><span>{desc}</span><span className="studio-open">Open workspace <ArrowUp size={13}/></span></button>)}</div></div>}

          {active === "Approval Queue" && <div className="page-section"><div className="eyebrow"><span className="eyebrow-line"/> YOUR FINAL SAY</div><h1>Approval <span>queue.</span></h1><p className="section-lead">Drafts saved here are not sent. Review and copy them yourself when ready.</p>{drafts.length === 0 ? <div className="empty-state"><ShieldCheck size={28}/><strong>Nothing waiting for approval</strong><span>Save an assistant response here when it is ready to review.</span></div> : <div className="draft-list">{drafts.map((draft)=><article className="draft-card" key={draft.id}><div className="draft-head"><div><strong>{draft.title}</strong><span><Clock3 size={12}/> {draft.createdAt}</span></div><button className="icon-btn" onClick={()=>setDrafts(drafts.filter(d=>d.id!==draft.id))} aria-label="Delete draft"><Trash2 size={16}/></button></div><p>{draft.body}</p><div className="draft-actions"><button className="secondary-btn" onClick={()=>navigator.clipboard.writeText(draft.body).then(()=>setNotice("Draft copied. It has not been sent."))}>Copy draft</button><button className="secondary-btn danger-btn" onClick={()=>setDrafts(drafts.filter(d=>d.id!==draft.id))}>Delete</button></div></article>)}</div>}</div>}
          {notice && <div className="notice"><Check size={14}/>{notice}<button onClick={()=>setNotice("")}><X size={13}/></button></div>}
        </div>
        <footer className="footer"><span>FAHIM AUTOPILOT AI <span className="footer-dot">·</span> BUILT FOR YOUR NEXT MOVE</span><span><span className="status-dot"/> AI access depends on your configured API key</span></footer>
      </section>
    </main>
  );
}
