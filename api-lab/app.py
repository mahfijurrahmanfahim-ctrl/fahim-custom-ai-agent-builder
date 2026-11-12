import time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="FAHIM Free API Lab", page_icon="🧪", layout="wide")
CATALOG_URL = "https://freeinference.dev/data/providers.json"
TIMEOUT = 25

PROVIDERS = {
    "OVHcloud AI — anonymous": {"kind":"openai","url":"https://oai.endpoints.kepler.ai.cloud.ovh.net/v1","model":"gpt-oss-20b","auth":"none","note":"Anonymous access is listed upstream at 2 requests/minute per IP/model; availability can vary."},
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

st.title("FAHIM FREE API LAB")
st.caption("Independent free AI provider catalogue and live API tester · Created by Fahim")
st.warning("No shared or leaked API keys are included. Enter only keys from your own provider accounts. This app does not write keys to files or a database; they are held in the active Streamlit session for the request. Use a trusted/private deployment.")

catalog_tab, test_tab, history_tab = st.tabs(["Provider catalogue", "Live API tests", "Test history"])

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
