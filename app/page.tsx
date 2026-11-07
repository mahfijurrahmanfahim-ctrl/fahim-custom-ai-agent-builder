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
    { label: "Content Studio", icon: WandSparkles },
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

          {active === "Client Finder" && <div className="page-section"><div className="eyebrow"><span className="eyebrow-line"/> GROW YOUR BUSINESS</div><h1>Find your next <span>great client.</span></h1><p className="section-lead">A focused workspace for discovering businesses that may need design, menus or promotional content.</p><div className="feature-panel"><div className="feature-icon"><Globe2 size={22}/></div><div><h3>Verified lead research</h3><p>Live business discovery is not connected yet. I will not show made-up businesses or pretend a lead is verified.</p><button className="primary-btn" onClick={() => sendMessage("Create a step-by-step lead research plan for restaurants, cafés, gyms and small businesses in Portugal and the UK. Explain how to verify each business and identify a public contact channel.")}>Build my lead research plan <ArrowUp size={15}/></button></div></div><div className="info-grid"><div className="info-tile"><Search size={18}/><strong>Find relevant businesses</strong><span>Prioritise restaurants, cafés and local brands.</span></div><div className="info-tile"><Check size={18}/><strong>Verify before saving</strong><span>Check that each business and contact source is real.</span></div><div className="info-tile"><ShieldCheck size={18}/><strong>Approve outreach</strong><span>Nothing is sent without your permission.</span></div></div></div>}

          {active === "Content Studio" && <div className="page-section"><div className="eyebrow"><span className="eyebrow-line"/> CREATIVE WORKSPACE</div><h1>Make something <span>stand out.</span></h1><p className="section-lead">Plan high-quality creative work for your clients and your own brand.</p><div className="studio-grid">{[{title:"Restaurant menu",desc:"Plan a polished, easy-to-read menu.",prompt:"Create a professional restaurant menu design brief. Ask me for the actual menu items, prices and brand details; never invent them.",icon:FileText},{title:"Social media campaign",desc:"Build a campaign with clear visual direction.",prompt:"Create a social media campaign concept for Fahim Graphic Design, including a visual direction, caption and call to action.",icon:ImageIcon},{title:"Promotional video",desc:"Develop a cinematic short-form video concept.",prompt:"Create a cinematic 30-second promotional video concept for Fahim Graphic Design with scene-by-scene visuals and voiceover.",icon:Activity},{title:"Client proposal",desc:"Prepare a clear proposal for a potential client.",prompt:"Create a professional graphic design service proposal template for a small business client. Leave unknown client details as placeholders.",icon:BriefcaseBusiness}].map(({title,desc,prompt,icon:Icon})=><button className="studio-card" key={title} onClick={()=>{setActive("Assistant");sendMessage(prompt);}}><span className="studio-icon"><Icon size={19}/></span><strong>{title}</strong><span>{desc}</span><span className="studio-open">Open workspace <ArrowUp size={13}/></span></button>)}</div></div>}

          {active === "Approval Queue" && <div className="page-section"><div className="eyebrow"><span className="eyebrow-line"/> YOUR FINAL SAY</div><h1>Approval <span>queue.</span></h1><p className="section-lead">Drafts saved here are not sent. Review and copy them yourself when ready.</p>{drafts.length === 0 ? <div className="empty-state"><ShieldCheck size={28}/><strong>Nothing waiting for approval</strong><span>Save an assistant response here when it is ready to review.</span></div> : <div className="draft-list">{drafts.map((draft)=><article className="draft-card" key={draft.id}><div className="draft-head"><div><strong>{draft.title}</strong><span><Clock3 size={12}/> {draft.createdAt}</span></div><button className="icon-btn" onClick={()=>setDrafts(drafts.filter(d=>d.id!==draft.id))} aria-label="Delete draft"><Trash2 size={16}/></button></div><p>{draft.body}</p><div className="draft-actions"><button className="secondary-btn" onClick={()=>navigator.clipboard.writeText(draft.body).then(()=>setNotice("Draft copied. It has not been sent."))}>Copy draft</button><button className="secondary-btn danger-btn" onClick={()=>setDrafts(drafts.filter(d=>d.id!==draft.id))}>Delete</button></div></article>)}</div>}</div>}
          {notice && <div className="notice"><Check size={14}/>{notice}<button onClick={()=>setNotice("")}><X size={13}/></button></div>}
        </div>
        <footer className="footer"><span>FAHIM AUTOPILOT AI <span className="footer-dot">·</span> BUILT FOR YOUR NEXT MOVE</span><span><span className="status-dot"/> AI access depends on your configured API key</span></footer>
      </section>
    </main>
  );
}
