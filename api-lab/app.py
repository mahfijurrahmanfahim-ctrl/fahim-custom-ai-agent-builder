import time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="FAHIM AI Studio", page_icon="⚡", layout="wide")

st.markdown("""
<style>
:root { --gold:#d8b45a; }
.stApp { background: radial-gradient(ellipse at 12% 0%, rgba(216,180,90,.13), transparent 34%), linear-gradient(155deg,#090b10 0%,#111722 55%,#090b10 100%); }
.block-container { max-width: 1320px; padding-top: 2rem; padding-bottom: 3rem; }
h1 { letter-spacing: -.045em; font-weight: 850 !important; }
[data-testid="stMetric"] { background:linear-gradient(145deg,rgba(255,255,255,.07),rgba(255,255,255,.025)); border:1px solid rgba(216,180,90,.22); padding:16px 18px; border-radius:16px; }
.stButton>button, .stDownloadButton>button { border-radius:12px; border:1px solid rgba(216,180,90,.45); transition:all .18s ease; }
.stButton>button[kind="primary"] { background:linear-gradient(100deg,#b68b35,#f0d48a); color:#111; font-weight:800; border:0; }
.stButton>button:hover { transform:translateY(-1px); border-color:#f0d48a; }
div[data-baseweb="tab-list"] { gap:8px; }
button[data-baseweb="tab"] { border-radius:10px 10px 0 0; padding:12px 18px; }
div[data-testid="stExpander"] { border:1px solid rgba(216,180,90,.18); border-radius:12px; }
.hero { padding:26px 28px; border:1px solid rgba(216,180,90,.32); border-radius:20px; background:linear-gradient(115deg,rgba(216,180,90,.13),rgba(255,255,255,.025)); margin:8px 0 22px; }
.hero-kicker { color:#e1c477; text-transform:uppercase; letter-spacing:.22em; font-size:11px; font-weight:800; }
.hero-title { font-size:clamp(30px,5vw,48px); line-height:1.04; font-weight:900; margin:10px 0; }
.hero-sub { color:#b9c0cb; font-size:14px; }
div[data-testid="stTextArea"] textarea { border-radius:14px; }
</style>
""", unsafe_allow_html=True)

CATALOG_URL = "https://freeinference.dev/data/providers.json"
TIMEOUT = 25

PROVIDERS = {
    "OVHcloud AI — anonymous": {"kind":"openai","url":"https://oai.endpoints.kepler.ai.cloud.ovh.net/v1","model":"gpt-oss-120b","auth":"none","note":"Independent live probes report successful anonymous chat calls. OVHcloud documents 2 requests/minute per IP and model."},
    "Kilo Gateway — anonymous free models": {"kind":"openai","url":"https://api.kilo.ai/api/gateway","model":"openrouter/free","auth":"none","note":"Independent live probes report successful anonymous calls. Gateway model availability and per-IP limits can change."},
    "Pollinations — openai-fast": {"kind":"openai","url":"https://text.pollinations.ai/openai","model":"openai-fast","auth":"none","note":"Independent live probes report successful anonymous calls. Public shared endpoint; availability, limits and acceptable-use terms can change."},
    "Google Gemini": {"kind":"openai","url":"https://generativelanguage.googleapis.com/v1beta/openai","model":"gemini-3.5-flash-lite","auth":"key","note":"Your own AI Studio key required. Check current EU terms and quotas."},
    "Groq": {"kind":"openai","url":"https://api.groq.com/openai/v1","model":"openai/gpt-oss-20b","auth":"key","note":"Free account/key required; quotas vary by model."},
    "OpenRouter free models": {"kind":"openai","url":"https://openrouter.ai/api/v1","model":"openrouter/free","auth":"key","note":"Your own key required; free-model daily limits apply."},
    "Mistral AI": {"kind":"openai","url":"https://api.mistral.ai/v1","model":"mistral-small-latest","auth":"key","note":"Free/experiment access depends on current account eligibility."},
    "NVIDIA NIM": {"kind":"openai","url":"https://integrate.api.nvidia.com/v1","model":"openai/gpt-oss-20b","auth":"key","note":"Developer account/key and per-model limits apply."},
    "Cohere": {"kind":"cohere","url":"https://api.cohere.com/v2","model":"command-r7b-12-2024","auth":"key","note":"Trial access is limited; check commercial-use terms."},
    "Cloudflare Workers AI": {"kind":"cloudflare","url":"https://api.cloudflare.com/client/v4/accounts","model":"@cf/openai/gpt-oss-120b","auth":"cloudflare","note":"Needs Cloudflare account ID and token; free daily neuron allowance applies."},
    "Z.AI / Zhipu": {"kind":"openai","url":"https://open.bigmodel.cn/api/paas/v4","model":"glm-4.7-flash","auth":"key","note":"Free model access and concurrency limits depend on account."},
    "Aion Labs": {"kind":"openai","url":"https://api.aionlabs.ai/v1","model":"aion-labs/aion-3.0-mini","auth":"key","note":"Free tier listed upstream; verify current signup and quotas."},
    "Gonka Broker": {"kind":"openai","url":"https://proxy.gonkabroker.com/v1","model":"deepseek-ai/DeepSeek-V4-Flash-0731","auth":"key","note":"Phone verification and shared/variable capacity may apply."},
    "ModelScope": {"kind":"openai","url":"https://api-inference.modelscope.cn/v1","model":"Qwen/Qwen3.5-27B","auth":"key","note":"Account binding/identity verification may be required."},
    "SiliconFlow": {"kind":"openai","url":"https://api.siliconflow.cn/v1","model":"tencent/Hunyuan-MT-7B","auth":"key","note":"Free model availability and identity requirements vary."},
}

def fetch_catalog():
    r = requests.get(CATALOG_URL, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or not isinstance(data.get("providers"), list):
        raise ValueError("Unexpected upstream catalogue format")
    return data

def flatten(data):
    rows = []
    for p in data.get("providers", []):
        models = p.get("models") or []
        names = [m.get("name", "") for m in models if isinstance(m, dict)]
        rows.append({
            "Provider": p.get("name", "Unknown"),
            "Free tier": p.get("free_type", "Not specified"),
            "Access": p.get("access_method", "Not specified"),
            "Channel": p.get("channel", "Not specified"),
            "Models": len(names),
            "Example models": ", ".join(names[:5]),
            "Verified": p.get("verified", "Unknown"),
            "Endpoint": p.get("base_url", ""),
            "Notes": p.get("notes", ""),
            "Source": p.get("url", ""),
        })
    return rows

def result_row(name, status, code, elapsed, model, answer="", detail=""):
    return {"provider":name,"status":status,"http":code,"latency_ms":elapsed,"model":model,"answer":str(answer)[:1200],"detail":str(detail)[:1000]}

def benchmark_provider(name, cfg, model, prompt, key="", runs=10):
    results = []
    for index in range(runs):
        row = test_provider(name, cfg, model, prompt, key)
        row["run"] = index + 1
        results.append(row)
        if index < runs - 1:
            # OVHcloud anonymous limit: 2 requests/minute per IP and model.
            time.sleep(31.0 if name.startswith("OVHcloud") else 1.0)
    return results

def test_provider(name, cfg, model, prompt, key="", account_id=""):
    start = time.perf_counter()
    try:
        headers = {"Content-Type":"application/json"}
        if cfg["auth"] in ("key", "cloudflare"):
            headers["Authorization"] = "Bearer " + key
        if cfg["kind"] == "openai":
            url = cfg["url"].rstrip("/") + "/chat/completions"
            body = {"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":180}
            r = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
            elapsed = round((time.perf_counter()-start)*1000)
            if r.ok:
                payload = r.json()
                answer = payload.get("choices",[{}])[0].get("message",{}).get("content","")
                if isinstance(answer, list):
                    answer = " ".join(str(x.get("text","")) for x in answer if isinstance(x,dict))
                return result_row(name, "PASS" if answer else "EMPTY", r.status_code, elapsed, model, answer, "Chat completion request returned.")
            return result_row(name, "FAIL", r.status_code, elapsed, model, "", r.text)
        if cfg["kind"] == "cohere":
            r = requests.post(cfg["url"].rstrip("/")+"/chat", headers=headers,
                json={"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":180}, timeout=TIMEOUT)
            elapsed = round((time.perf_counter()-start)*1000)
            if r.ok:
                answer = r.json().get("message",{}).get("content",[{}])[0].get("text","")
                return result_row(name, "PASS" if answer else "EMPTY", r.status_code, elapsed, model, answer, "Cohere v2 chat returned.")
            return result_row(name, "FAIL", r.status_code, elapsed, model, "", r.text)
        if cfg["kind"] == "cloudflare":
            url = cfg["url"].rstrip("/")+"/"+account_id+"/ai/v1/chat/completions"
            r = requests.post(url, headers=headers,
                json={"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":180}, timeout=TIMEOUT)
            elapsed = round((time.perf_counter()-start)*1000)
            if r.ok:
                answer = r.json().get("choices",[{}])[0].get("message",{}).get("content","")
                return result_row(name, "PASS" if answer else "EMPTY", r.status_code, elapsed, model, answer, "Cloudflare chat completion returned.")
            return result_row(name, "FAIL", r.status_code, elapsed, model, "", r.text)
        return result_row(name, "UNSUPPORTED", "", "", model, "", "No adapter for this API format.")
    except requests.Timeout:
        return result_row(name, "TIMEOUT", "", round((time.perf_counter()-start)*1000), model, "", "Request timed out.")
    except Exception as exc:
        return result_row(name, "ERROR", "", round((time.perf_counter()-start)*1000), model, "", repr(exc))

st.markdown("""<div class="hero"><div class="hero-kicker">Fahim · Personal AI workspace</div><div class="hero-title">FAHIM AI STUDIO</div><div class="hero-sub">One workspace for real AI requests, provider testing and free-tier discovery.</div></div>""", unsafe_allow_html=True)
st.caption("Created by Fahim · Free-first infrastructure · No bundled or shared API keys")
st.warning("No shared or leaked API keys are included. Enter only keys from your own provider accounts. This app does not write keys to files or a database; they are held in the active Streamlit session for the request. Use a trusted/private deployment.")

workspace_tab, catalog_tab, test_tab, history_tab = st.tabs(["⚡ AI Workspace", "Provider catalogue", "Live API tests", "Test history"])


with workspace_tab:
    st.subheader("Command centre")
    st.caption("Send one prompt. The workspace tries configured providers in order and reports exactly which one answered.")
    w1, w2, w3 = st.columns(3)
    with w1:
        wk_groq = st.text_input("Groq key (optional)", type="password", key="workspace_groq")
    with w2:
        wk_gemini = st.text_input("Gemini key (optional)", type="password", key="workspace_gemini")
    with w3:
        wk_openrouter = st.text_input("OpenRouter key (optional)", type="password", key="workspace_openrouter")
    command = st.text_area("What do you want the AI to do?", placeholder="Example: Create 5 premium Instagram campaign ideas for a small café in Porto...", height=130, key="workspace_command")
    run_col, clear_col = st.columns([3,1])
    with run_col:
        run_command = st.button("Run command  →", type="primary", use_container_width=True, key="workspace_run")
    with clear_col:
        if st.button("Clear", use_container_width=True, key="workspace_clear"):
            st.session_state.workspace_command = ""
            st.session_state.pop("workspace_result", None)
            st.rerun()
    if run_command:
        if not command.strip():
            st.warning("Enter a command first.")
        else:
            queue = []
            if wk_groq.strip():
                queue.append(("Groq", PROVIDERS["Groq"], PROVIDERS["Groq"]["model"], wk_groq.strip()))
            if wk_gemini.strip():
                queue.append(("Google Gemini", PROVIDERS["Google Gemini"], PROVIDERS["Google Gemini"]["model"], wk_gemini.strip()))
            if wk_openrouter.strip():
                queue.append(("OpenRouter free models", PROVIDERS["OpenRouter free models"], PROVIDERS["OpenRouter free models"]["model"], wk_openrouter.strip()))
            queue.extend([
                ("OVHcloud AI — anonymous", PROVIDERS["OVHcloud AI — anonymous"], PROVIDERS["OVHcloud AI — anonymous"]["model"], ""),
                ("Kilo Gateway — anonymous free models", PROVIDERS["Kilo Gateway — anonymous free models"], PROVIDERS["Kilo Gateway — anonymous free models"]["model"], "")
            ])
            attempts = []
            answer = ""
            progress = st.progress(0, text="Connecting to available AI providers...")
            for idx, (provider_name, provider_cfg, model_id, api_key) in enumerate(queue):
                result = test_provider(provider_name, provider_cfg, model_id, command.strip(), api_key)
                attempts.append(result)
                progress.progress((idx + 1) / len(queue), text=f"Trying {provider_name} · {idx + 1}/{len(queue)}")
                if result["status"] == "PASS" and result["answer"].strip():
                    answer = result["answer"]
                    st.session_state.workspace_result = {"answer":answer,"provider":provider_name,"model":model_id,"latency":result["latency_ms"],"attempts":attempts}
                    break
            progress.empty()
            if not answer:
                st.session_state.workspace_result = {"answer":"","provider":"","model":"","latency":"","attempts":attempts}
    if st.session_state.get("workspace_result"):
        wr = st.session_state.workspace_result
        st.divider()
        if wr["answer"]:
            st.success("Response received · " + wr["provider"])
            st.markdown(wr["answer"])
            st.caption(f"Model: {wr['model']} · Response time: {wr['latency']} ms · Providers tried: {len(wr['attempts'])}")
        else:
            st.error("No provider returned a usable answer. See the attempts below; no response has been fabricated.")
        with st.expander("Provider diagnostics"):
            st.dataframe(pd.DataFrame(wr["attempts"])[["provider","status","http","latency_ms","model","detail"]], use_container_width=True, hide_index=True)
    st.divider()
    st.subheader("Creative tools")
    ci, cv, cs = st.columns(3)
    with ci:
        st.markdown("**Image generation**")
        st.caption("Not connected to a verified free image API in this build. No fake Generate button.")
        st.link_button("Open free image workspace", "https://huggingface.co/spaces", use_container_width=True)
    with cv:
        st.markdown("**Video generation**")
        st.caption("Use a public hosted generation queue; wait times and availability vary.")
        st.link_button("Explore Wan video demo", "https://wan.video/", use_container_width=True)
    with cs:
        st.markdown("**Web research**")
        st.caption("Search provider integration is not configured yet. Open a real search engine.")
        st.link_button("Open web search", "https://www.google.com/", use_container_width=True)

with catalog_tab:
    c1, c2 = st.columns([3,1])
    with c1:
        st.subheader("Live free-inference directory")
        st.caption("Source: Free Inference machine-readable directory. Entries can include tools and model hosts, not only direct chat APIs.")
    with c2:
        refresh = st.button("Refresh directory", use_container_width=True)
    if "catalog" not in st.session_state or refresh:
        try:
            with st.spinner("Loading upstream provider catalogue..."):
                st.session_state.catalog = fetch_catalog()
                st.session_state.catalog_error = ""
        except Exception as exc:
            st.session_state.catalog_error = str(exc)
    if st.session_state.get("catalog"):
        data = st.session_state.catalog
        rows = flatten(data)
        st.metric("Providers listed upstream", len(rows))
        st.caption("Directory verification date: "+str(data.get("verified","not provided")))
        query = st.text_input("Filter by provider, model, endpoint or note")
        if query.strip():
            q = query.casefold()
            rows = [r for r in rows if q in " ".join(str(v) for v in r.values()).casefold()]
        df = pd.DataFrame(rows)
        if not df.empty:
            st.dataframe(df[["Provider","Free tier","Access","Channel","Models","Example models","Verified"]], use_container_width=True, hide_index=True)
            st.download_button("Download directory CSV", df.to_csv(index=False).encode(), "fahim-free-api-directory.csv", "text/csv")
            with st.expander("Details, endpoints and source links"):
                for row in rows:
                    st.markdown("**"+row["Provider"]+"** · "+row["Free tier"]+" · access: "+str(row["Access"]))
                    st.caption(row["Notes"])
                    if row["Endpoint"]:
                        st.code(row["Endpoint"])
                    if row["Source"]:
                        st.markdown("[Provider source]("+row["Source"]+")")
        else:
            st.info("No matching entries.")
    elif st.session_state.get("catalog_error"):
        st.error("Could not load the directory: "+st.session_state.catalog_error)

with test_tab:
    st.subheader("Run an actual API request")
    selected = st.selectbox("Provider", list(PROVIDERS.keys()))
    cfg = PROVIDERS[selected]
    st.caption(cfg["note"])
    model = st.text_input("Model ID", value=cfg["model"])
    key = ""
    account_id = ""
    if cfg["auth"] in ("key","cloudflare"):
        key = st.text_input("Your API key / token", type="password")
    if cfg["auth"] == "cloudflare":
        account_id = st.text_input("Cloudflare Account ID")
    prompt = st.text_area("Test prompt", "Reply with exactly: FAHIM API TEST SUCCESS", height=90)
    if st.button("Test selected provider", type="primary", use_container_width=True):
        if not model.strip() or not prompt.strip():
            st.warning("Enter a model ID and prompt.")
        elif cfg["auth"] in ("key","cloudflare") and not key.strip():
            st.warning("This provider requires your own key/token.")
        elif cfg["auth"] == "cloudflare" and not account_id.strip():
            st.warning("Cloudflare Account ID is required.")
        else:
            with st.spinner("Sending test request..."):
                result = test_provider(selected,cfg,model.strip(),prompt.strip(),key.strip(),account_id.strip())
            st.session_state.setdefault("history", []).insert(0,result)
            st.session_state.last_result = result
    if st.button("Test all keyless providers", use_container_width=True):
        for name, item in PROVIDERS.items():
            if item["auth"] == "none":
                with st.spinner("Testing "+name+"..."):
                    result = test_provider(name,item,item["model"],prompt.strip())
                st.session_state.setdefault("history", []).insert(0,result)
        if st.session_state.get("history"):
            st.session_state.last_result = st.session_state.history[0]
    if st.session_state.get("last_result"):
        result = st.session_state.last_result
        st.divider()
        st.markdown("**"+result["provider"]+" — "+result["status"]+"**")
        st.write("HTTP: "+str(result["http"])+" · Latency: "+str(result["latency_ms"])+" ms · Model: "+result["model"])
        st.caption(result["detail"])
        if result["answer"]:
            st.code(result["answer"])


    st.divider()
    st.subheader("Six-provider repeat benchmark")
    st.caption("Runs 10 small chat requests per provider (60 total). Enter your own keys; they are not saved to disk or database.")
    gemini_key = st.text_input("Gemini API key for benchmark", type="password", key="bench_gemini_key")
    groq_key = st.text_input("Groq API key for benchmark", type="password", key="bench_groq_key")
    openrouter_key = st.text_input("OpenRouter API key for benchmark", type="password", key="bench_openrouter_key")
    benchmark_names = ["Groq", "Google Gemini", "OpenRouter free models", "OVHcloud AI — anonymous", "Kilo Gateway — anonymous free models", "Pollinations — openai-fast"]
    if st.button("Run 10 tests per provider (60 requests)", type="primary", use_container_width=True):
        credentials = {"Groq": groq_key.strip(), "Google Gemini": gemini_key.strip(), "OpenRouter free models": openrouter_key.strip()}
        missing = [name for name, value in credentials.items() if not value]
        if missing:
            st.error("Enter your own keys for: " + ", ".join(missing))
        else:
            all_rows = []
            progress = st.progress(0, text="Preparing benchmark...")
            total = len(benchmark_names) * 10
            count = 0
            for provider_name in benchmark_names:
                provider_cfg = PROVIDERS[provider_name]
                rows = benchmark_provider(provider_name, provider_cfg, provider_cfg["model"], "Reply with exactly: OK", credentials.get(provider_name, ""), runs=10)
                for row in rows:
                    all_rows.append(row)
                    count += 1
                    progress.progress(count / total, text=f"Testing {provider_name}: {count}/{total}")
            st.session_state.benchmark_rows = all_rows
            st.session_state.setdefault("history", []).extend(reversed(all_rows))
            progress.empty()
            st.success("Benchmark finished. Review the results below.")
    if st.session_state.get("benchmark_rows"):
        bdf = pd.DataFrame(st.session_state.benchmark_rows)
        summary = bdf.groupby("provider").agg(attempts=("status", "count"), passes=("status", lambda x: int((x == "PASS").sum())), avg_ms=("latency_ms", "mean"), median_ms=("latency_ms", "median"), min_ms=("latency_ms", "min"), max_ms=("latency_ms", "max")).reset_index()
        summary["success_rate_%"] = (summary["passes"] / summary["attempts"] * 100).round(1)
        for col in ["avg_ms", "median_ms", "min_ms", "max_ms"]:
            summary[col] = summary[col].round(0).astype("Int64")
        st.dataframe(summary.sort_values(["success_rate_%", "median_ms"], ascending=[False, True]), use_container_width=True, hide_index=True)
        st.download_button("Download benchmark detail CSV", bdf.to_csv(index=False).encode(), "fahim-six-provider-benchmark.csv", "text/csv")

with history_tab:
    history = st.session_state.get("history",[])
    if history:
        df = pd.DataFrame(history)
        st.dataframe(df[["provider","status","http","latency_ms","model","detail"]], use_container_width=True, hide_index=True)
        st.download_button("Download test results CSV", df.to_csv(index=False).encode(), "fahim-api-test-results.csv", "text/csv")
        if st.button("Clear history"):
            st.session_state.history = []
            st.session_state.pop("last_result",None)
            st.rerun()
    else:
        st.caption("No tests run in this session.")

st.divider()
st.caption("PASS means this exact request worked at test time. It does not guarantee future uptime, unlimited quota, commercial rights or privacy suitability. Always check provider terms.")
