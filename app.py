# Cadas Resonance Studio — app.py
# Streamlit app for CLICK -> STAY -> RETURN content planning.
# ClarioHub OpenAI-compatible API integration. Without an API key, the app runs in demo mode.
# Run: pip install streamlit requests && streamlit run app.py

import json
import random
import re
import textwrap
from datetime import datetime

import requests
import streamlit as st

APP_NAME = "CADAS RESONANCE STUDIO"
DEFAULT_MODEL = "clario/deepseek-v4-flash"
CLARIOHUB_BASE_URL = "https://clariohub.id/v1"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="💀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- UI STYLE -----------------------------
st.markdown("""
<style>
    :root {
        --ink: #18223d;
        --muted: #586681;
        --line: rgba(117, 137, 190, .28);
        --blue: #315ee8;
        --violet: #7751d8;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 8% 4%, rgba(105, 145, 255, .23), transparent 32%),
            radial-gradient(ellipse at 94% 12%, rgba(177, 119, 255, .20), transparent 29%),
            radial-gradient(ellipse at 72% 90%, rgba(91, 211, 221, .16), transparent 32%),
            linear-gradient(135deg, #edf2ff 0%, #f5f0ff 48%, #eaf8fb 100%);
        color: var(--ink);
        background-attachment: fixed;
    }
    [data-testid="stHeader"] { background: rgba(239,243,255,.72); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e5ebff 0%, #f0eaff 52%, #e4f6fb 100%);
        border-right: 1px solid rgba(115, 130, 190, .24);
    }
    [data-testid="stSidebar"] * { color: #202b4b; }
    .block-container { max-width: 1200px; padding-top: 1.25rem; padding-bottom: 3rem; }
    .hero {
        position: relative; overflow: hidden;
        padding: 1.55rem 1.65rem; border-radius: 22px;
        background: linear-gradient(115deg, rgba(255,255,255,.92), rgba(229,235,255,.88) 48%, rgba(238,226,255,.91));
        border: 1px solid rgba(129, 143, 207, .32); margin-bottom: 1.1rem;
        box-shadow: 0 14px 34px rgba(64, 74, 145, .12);
    }
    .hero:after {
        content: ""; position: absolute; width: 190px; height: 190px; right: -48px; top: -78px;
        border-radius: 50%; border: 28px solid rgba(116, 91, 225, .09);
        box-shadow: 0 0 0 22px rgba(75, 137, 232, .05), 0 0 0 48px rgba(75, 137, 232, .035);
        pointer-events: none;
    }
    .hero h1 { margin: 0; font-size: 2rem; color: #26366e; letter-spacing: -.035em; }
    .hero p { margin: .5rem 0 0; color: #52617f; }
    .pill {
        display: inline-block; padding: .25rem .65rem; margin: .15rem;
        border: 1px solid rgba(105, 117, 197, .25); border-radius: 999px;
        color: #38458c; background: linear-gradient(135deg, #fff, #edf0ff); font-size: .82rem;
        box-shadow: 0 3px 8px rgba(80, 91, 165, .06);
    }
    .stage {
        border: 1px solid rgba(117, 137, 190, .25);
        background: linear-gradient(145deg, rgba(255,255,255,.91), rgba(244,246,255,.86));
        border-radius: 16px; padding: 1rem 1.05rem; min-height: 100px;
        box-shadow: 0 7px 20px rgba(62, 75, 140, .07);
    }
    .stage h4 { margin: 0 0 .35rem; color: #3d4da0; }
    .muted { color: var(--muted); font-size: .9rem; }
    div[data-testid="stExpander"] {
        border: 1px solid rgba(117, 137, 190, .25);
        border-radius: 14px; background: rgba(255,255,255,.56);
    }
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea,
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="stNumberInput"] input {
        border-radius: 10px; border-color: rgba(117, 137, 190, .36);
        background: rgba(255,255,255,.86);
    }
    div.stButton > button {
        border-radius: 11px; font-weight: 700; min-height: 2.75rem;
        border: 1px solid rgba(89, 105, 193, .28);
        box-shadow: 0 4px 10px rgba(65, 76, 151, .08);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    div.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 7px 16px rgba(65, 76, 151, .15); }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(115deg, #315ee8, #7751d8); color: white; border: none;
    }
    div[data-testid="stAlert"] { border-radius: 12px; }
    hr { border-color: rgba(117, 137, 190, .22); }
    @media (max-width:700px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .hero { padding: 1.15rem; }
        .hero h1 { font-size: 1.55rem; }
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------- STATE -----------------------------
def init_state():
    defaults = {
        "ideas": [],
        "selected_title": "",
        "selected_idea": {},
        "hooks": [],
        "selected_hook": "",
        "story": {},
        "flow_prompts": [],
        "broll": [],
        "last_signature": "",
        "notice": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

def clear_from(stage):
    """Invalidate downstream results when upstream choices change."""
    order = ["ideas", "hooks", "story", "flow_prompts", "broll"]
    if stage in order:
        idx = order.index(stage)
        for key in order[idx:]:
            if key == "ideas":
                st.session_state.ideas = []
                st.session_state.selected_title = ""
                st.session_state.selected_idea = {}
                st.session_state.chosen_idea_title = ""
            elif key == "hooks":
                st.session_state.hooks = []
                st.session_state.selected_hook = ""
            elif key == "story":
                st.session_state.story = {}
            elif key == "flow_prompts":
                st.session_state.flow_prompts = []
            elif key == "broll":
                st.session_state.broll = []

def invalidate_downstream(stage):
    order = ["hooks", "story", "flow_prompts", "broll"]
    idx = order.index(stage)
    for key in order[idx:]:
        if key == "hooks":
            st.session_state.hooks = []
            st.session_state.selected_hook = ""
        elif key == "story":
            st.session_state.story = {}
        elif key == "flow_prompts":
            st.session_state.flow_prompts = []
        elif key == "broll":
            st.session_state.broll = []

# ----------------------------- GEMINI -----------------------------
def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        raise

def clariohub_generate(prompt, api_key, model, temperature=0.85):
    """Call ClarioHub's OpenAI-compatible chat completions endpoint."""
    if not api_key:
        raise RuntimeError("API key ClarioHub belum diisi. Isi key di panel pengaturan atau gunakan mode demo.")
    url = f"{CLARIOHUB_BASE_URL}/chat/completions"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        json={
            "model": model.strip() or DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": "You are a precise short-video creative producer. Follow the user's requested JSON schema exactly. Return valid JSON only, without markdown fences."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        },
        timeout=120,
    )
    if response.status_code != 200:
        try:
            data = response.json()
            detail = data.get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"ClarioHub API error ({response.status_code}): {detail}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "\n".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
        return extract_json(str(content))
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Respons ClarioHub kosong atau bukan JSON yang valid.") from exc

def ai_or_demo(prompt, api_key, model, demo_fn, temperature=0.85):
    if api_key:
        return clariohub_generate(prompt, api_key, model, temperature)
    return demo_fn()

# ----------------------------- PROMPT HELPERS -----------------------------
def mode_language(mode):
    if mode == "Global Skeleton":
        return "English dialogue and English titles; instructions may be in English."
    if mode == "Indonesia Lokal":
        return "Semua judul, premis, dialog, hook, CTA, dan deskripsi cerita wajib menggunakan Bahasa Indonesia natural. Humor lokal Indonesia, dialog ringkas. Prompt teknis visual boleh berbahasa Inggris bila membantu generator video."
    return "Sediakan versi Indonesia dan versi English secara terpisah; jangan mencampur bahasa dalam satu dialog atau satu versi cerita."

def realism_rules(mode):
    return """
VISUAL RULES — MANDATORY:
- Photorealistic live-action look or highly realistic cinematic CGI with believable materials.
- NOT cartoon, NOT Pixar, NOT anime, NOT illustration, NOT toy-like plastic, NOT flat 2D.
- Realistic anatomy/materials, detailed textures, physically plausible lighting, cinematic lensing.
- For skeleton stories, use a detailed realistic anatomical skeleton with natural bone texture;
  it must not look like a cartoon mascot or a plastic toy.
- Keep the same character identity, clothing/accessories, proportions, and location across shots.
- Vertical 9:16 by default, sharp focus on the subject, no blur unless motivated by camera movement.
- Do not generate subtitles, logos, watermarks, or extra text inside the video.
"""

def current_config():
    return {
        "mode": st.session_state.get("mode", "Global Skeleton"),
        "theme": st.session_state.get("theme", "Absurd Comedy"),
        "subtheme": st.session_state.get("subtheme", "Everyday disaster"),
        "duration": st.session_state.get("duration", 20),
        "audience": st.session_state.get("audience", "General audience"),
        "style": st.session_state.get("style", "Realistic cinematic"),
        "goal": st.session_state.get("goal", "Subscriber growth"),
        "character": st.session_state.get("character", "Overconfident Skeleton"),
        "setting": st.session_state.get("setting", "Everyday location"),
        "humor": st.session_state.get("humor", "Absurd, fast-paced, visual"),
        "language": mode_language(st.session_state.get("mode", "Global Skeleton")),
    }

def config_signature(cfg):
    return json.dumps(cfg, sort_keys=True, ensure_ascii=False)

def ensure_current():
    cfg = current_config()
    sig = config_signature(cfg)
    if st.session_state.last_signature and sig != st.session_state.last_signature:
        clear_from("ideas")
    st.session_state.last_signature = sig

def make_ideas_prompt(cfg, count):
    return f"""
You are the creative strategist for {APP_NAME}.
Generate exactly {count} genuinely different short-video concepts.
Return valid JSON only with this schema:
{{
 "ideas":[
  {{
   "title":"specific clickable title",
   "premise":"one-sentence premise",
   "hook":"what viewers see/hear in the first 1 second",
   "conflict":"central problem",
   "twist":"payoff/reversal",
   "series_potential":"a concrete way this could become an episode series",
   "primary_goal":"{cfg['goal']}"
  }}
 ]
}}
CHANNEL: {cfg['mode']}
THEME: {cfg['theme']} / {cfg['subtheme']}
CHARACTER: {cfg['character']}
SETTING: {cfg['setting']}
AUDIENCE: {cfg['audience']}
HUMOR: {cfg['humor']}
LANGUAGE: {cfg['language']}
Create distinct concepts, not the same premise with different titles. Avoid generic clickbait.
Each hook must be immediately understandable and visually filmable. Every concept needs a clear payoff. For subscriber-growth goals, optimize for an instant visual stop, escalating curiosity, a memorable payoff, and a natural explicit subscribe/like invitation in the final beat.
{realism_rules(cfg['mode'])}
"""

def demo_ideas(cfg, count):
    """Settings-aware fallback when no API key is supplied; never return a fixed unrelated title pool."""
    subtheme = re.sub(r"\s+", " ", str(cfg.get("subtheme", "kejadian absurd")).strip()).strip(" .,!?:;")
    if not subtheme:
        subtheme = str(cfg.get("theme", "kejadian absurd"))
    character = str(cfg.get("character", "karakter utama"))
    setting = str(cfg.get("setting", "lokasi sesuai subtema"))
    theme = str(cfg.get("theme", "Komedi"))
    goal = str(cfg.get("goal", "Subscriber growth"))
    local = cfg.get("mode") == "Indonesia Lokal"

    # Keep custom user wording as the source of truth. Titles are varied from that
    # wording instead of pulling unrelated legacy demo examples such as kos/warung.
    short_topic = subtheme[:76].strip()
    title_patterns = (
        f"{short_topic.upper()} — MISI BERANTAKAN",
        f"KETIKA {short_topic.upper()} MALAH KACAU",
        f"{short_topic.upper()}: ADA YANG TIDAK BERES",
        f"MISI MUSTAHIL: {short_topic.upper()}",
        f"ENDING TAK TERDUGA SAAT {short_topic.upper()}",
        f"{short_topic.upper()} TAPI SEMUANYA SALAH",
        f"RAHASIA DI BALIK {short_topic.upper()}",
        f"{short_topic.upper()} BERUJUNG PETAKA LUCU",
        f"SIAPA SANGKA {short_topic.upper()} JADI BEGINI",
        f"{short_topic.upper()}: DETIK-DETIK PALING KACAU",
    )
    conflict_templates = [
        f"Rencana {subtheme} terganggu oleh masalah tak terduga di {setting}.",
        f"{character} tidak bisa menyelesaikan {subtheme} semudah yang dibayangkan.",
        f"Satu keputusan konyol membuat situasi {subtheme} makin kacau.",
        f"Ada aturan/halangan di {setting} yang merusak rencana {subtheme}.",
        f"Saat {subtheme} hampir berhasil, muncul masalah yang mempermalukan {character}.",
        f"Semua karakter salah paham tentang tujuan {subtheme}.",
        f"Sebuah benda penting hilang ketika {subtheme} sedang berlangsung.",
        f"{character} mencoba menutupi kesalahan, tetapi justru memperbesar masalah.",
        f"Orang di sekitar salah mengira kejadian {subtheme} sebagai sesuatu yang lain.",
        f"Rencana sederhana di {setting} berubah menjadi kekacauan berantai.",
    ]
    twist_templates = [
        f"Ternyata masalahnya berasal dari hal kecil yang sejak awal terlihat di {setting}.",
        f"{character} justru menjadi penyebab utama kekacauan yang ingin ia hentikan.",
        f"Rencana itu berhasil, tetapi hasil akhirnya malah berlawanan dengan tujuan awal.",
        f"Orang yang dianggap mengganggu ternyata satu-satunya yang paham situasi.",
        f"Benda yang dicari ternyata sudah dibawa karakter sejak awal.",
        f"Semua orang panik, padahal pemicunya adalah kesalahpahaman konyol.",
        f"Akhirnya {character} harus mengulang kejadian dari awal untuk memperbaiki kesalahan.",
        f"Petunjuk twist terlihat di detik pertama dan baru masuk akal saat ditonton ulang.",
        f"Yang dikira kegagalan ternyata justru membuka masalah yang lebih lucu.",
        f"Karakter paling percaya diri malah meminta bantuan penonton untuk menyelesaikannya.",
    ]
    ideas = []
    indices = list(range(len(title_patterns)))
    random.shuffle(indices)
    for i in indices[:max(1, min(count, len(title_patterns)))]:
        title = title_patterns[i]
        conflict = conflict_templates[i]
        twist = twist_templates[i]
        if local:
            premise = f"{subtheme}. Cerita berlangsung di {setting}, dengan {character} sebagai karakter utama; kejadian berkembang menjadi komedi sesuai tema {theme}."
            hook = f"{character.upper()} LANGSUNG MENGHADAPI MASALAH: {subtheme.upper()}!"
            series = f"Episode lanjutan mengeksplorasi masalah baru dari dunia cerita '{subtheme}', tetap memakai karakter dan lokasi yang sama."
        else:
            premise = f"{subtheme}. The story takes place at {setting}, starring {character}, with a {theme} payoff."
            hook = f"{character.upper()} FACES THIS PROBLEM RIGHT NOW: {subtheme.upper()}!"
            series = f"A follow-up episode explores another problem from the same '{subtheme}' premise, keeping the selected character and setting."
        ideas.append({
            "title": title,
            "premise": premise,
            "hook": hook,
            "conflict": conflict,
            "twist": twist,
            "series_potential": series,
            "primary_goal": goal,
        })
    return {"ideas": ideas}

def make_hooks_prompt(cfg, idea):
    return f"""
Generate exactly 3 alternative first-second hooks for this short-video concept, ranked strongest first. The FIRST hook must be the strongest and will be selected automatically; the user will not choose from a list.
Return JSON only: {{"hooks":[{{"hook":"...","visual":"...","curiosity":"...","strength":"..."}},...]}}
SELECTED CONCEPT — SOURCE OF TRUTH (do not replace it with another idea):
Title: {idea.get('title')}
Premise: {idea.get('premise')}
Opening event: {idea.get('hook')}
Conflict: {idea.get('conflict')}
Twist/payoff: {idea.get('twist')}
Channel: {cfg['mode']}; theme: {cfg['theme']}/{cfg['subtheme']}; character: {cfg['character']}; setting: {cfg['setting']}.
Language: {cfg['language']}
Create 3 different hooks for THIS EXACT concept. Every hook's dialogue and visual must match its premise, characters, conflict, and setting. Never introduce a pocong, kos, warung, skeleton, or any other motif unless it is explicitly in the selected idea.
Hooks must be immediately understandable, filmable, and not rely only on shouting. Do not reveal the whole punchline in the hook.
{realism_rules(cfg['mode'])}
"""

def demo_hooks(cfg, idea):
    """Build fallback hooks from the selected idea; never use an unrelated hard-coded story."""
    title = str(idea.get("title", "Ide pilihan")).strip()
    premise = str(idea.get("premise", "")).strip()
    seed_visual = str(idea.get("hook", "")).strip()
    conflict = str(idea.get("conflict", "")).strip()
    twist = str(idea.get("twist", "")).strip()
    is_local = cfg.get("mode") == "Indonesia Lokal"

    if is_local:
        hooks = [
            {"hook": seed_visual or f"LAH, KOK BISA?! {title.upper()}!", "visual": seed_visual or premise,
             "curiosity": f"Apa akibat dari kejadian ini dalam cerita {title.lower()}?", "strength": "Hook mengambil kejadian spesifik dari ide terpilih, bukan judul acak."},
            {"hook": conflict or f"ADA MASALAH DI {title.upper()}!", "visual": conflict or seed_visual or premise,
             "curiosity": f"Bagaimana karakter menyelesaikan masalah ini?", "strength": "Konflik spesifik dari ide terpilih langsung terlihat."},
            {"hook": f"TUNGGU—AKHIRNYA MALAH BEGINI?!", "visual": twist or premise,
             "curiosity": f"Twist apa yang muncul dari {title.lower()}?", "strength": "Menjanjikan kejutan yang berasal dari payoff ide ini."}
        ]
    else:
        hooks = [
            {"hook": f"WAIT—{title.upper()}?!", "visual": seed_visual or premise,
             "curiosity": f"What happens in {title.lower()}?", "strength": "Starts directly with the selected concept."},
            {"hook": conflict or f"THIS WAS NOT SUPPOSED TO HAPPEN!", "visual": conflict or seed_visual or premise,
             "curiosity": "How will the character solve this specific problem?", "strength": "Uses the conflict from the selected idea."},
            {"hook": "THE ENDING MAKES NO SENSE… UNTIL YOU SEE IT!", "visual": twist or premise,
             "curiosity": f"What is the twist in {title.lower()}?", "strength": "Teases the selected concept's actual payoff."}
        ]
    return {"hooks": hooks}

def make_story_prompt(cfg, idea, hook):
    return f"""
Write a complete short-video story using the selected title and automatically selected strongest hook exactly as the source of truth. Total target duration: {cfg['duration']} seconds. Build a complete timeline covering 0 to {cfg['duration']} seconds, divided into clear beats with no gaps or overlaps. Split the story into an immediate hook, escalating conflict, a strong twist/punchline, and a natural replay loop. The CTA IS REQUIRED, not optional: it must explicitly say subscribe/subscribe channel AND like, in the language of the channel, while giving a concrete funny reason to rewatch. Never omit the subscription request. Make it feel like part of the scene, not generic begging.
Return valid JSON only:
{{
 "title":"{idea.get('title','')}",
 "logline":"one sentence",
 "hook":{{"visual":"...","dialogue":"...","duration_seconds":1}},
 "beats":[
  {{"start":0,"end":1,"purpose":"HOOK","visual":"...","action":"...","dialogue":"...","sound":"..."}},
  {{"start":1,"end":3,"purpose":"CONTEXT","visual":"...","action":"...","dialogue":"...","sound":"..."}},
  {{"start":3,"end":6,"purpose":"CONFLICT","visual":"...","action":"...","dialogue":"...","sound":"..."}},
  {{"start":6,"end":8,"purpose":"ESCALATION","visual":"...","action":"...","dialogue":"...","sound":"..."}},
  {{"start":8,"end":10,"purpose":"PAYOFF","visual":"...","action":"...","dialogue":"...","sound":"..."}}
 ],
 "punchline":"...",
 "cta":"MUST explicitly invite the viewer to SUBSCRIBE and LIKE, using this story’s character/object/twist; add a funny reason to rewatch. No generic template.",
 "return_potential":"...",
 "continuity_notes":["..."]
}}
Selected concept: {json.dumps(idea, ensure_ascii=False)}
Selected hook: {json.dumps(hook, ensure_ascii=False)}
Channel: {cfg['mode']}; theme: {cfg['theme']}/{cfg['subtheme']}; character: {cfg['character']};
setting: {cfg['setting']}; target: {cfg['audience']}; goal: {cfg['goal']}; humor: {cfg['humor']}.
Language: {cfg['language']}
Write a story whose timeline exactly matches the selected {cfg['duration']}-second duration, with a beginning, escalating conflict, satisfying punchline, CTA, and replay loop.
CTA BLUEPRINT (must be custom for this exact title, not a reusable template):
1) CALLBACK: mention the specific character, object, problem, or twist from this story.
2) JOKE/PUNCH: turn that callback into a short funny or surprising line.
3) NATURAL ACTION: weave in a light subscribe/like invitation as part of the joke or character's reaction, never a detached generic request.
4) REWATCH LOOP: end with a visual/dialogue cue that naturally connects to the opening or reveals a detail worth noticing again.
MANDATORY CTA CHECKLIST: (a) explicitly ask the viewer to SUBSCRIBE to the channel, using "subscribe" or the natural local equivalent; (b) explicitly ask for a LIKE; (c) give a story-specific funny reason to replay/watch again; (d) the CTA must mention/callback to this exact title's character, prop, or twist. All four are required. The CTA wording must differ for every title and fit the character's voice. Never promise rewards, threaten viewers, or make false claims.
No filler, no long exposition, no unrelated jokes. The selected title must remain unchanged.
STRICT CONTINUITY: every beat, prop, character, visual prompt, punchline, and CTA must come from the selected concept above. Do not switch to a different idea or insert generic demo scenes. The hook must lead into the exact selected conflict and twist. The CTA must fit this scene and be woven into the joke; if it does not fit naturally, keep the joke but STILL include a short explicit subscribe + like invitation in the character's voice. The subscribe request must never be omitted.
{realism_rules(cfg['mode'])}
"""

def demo_story(cfg, idea, hook):
    """Create a coherent demo story from the selected idea and hook, not a fixed unrelated template."""
    title = str(idea.get("title", "Ide pilihan")).strip()
    premise = str(idea.get("premise", "")).strip()
    seed_hook = str(idea.get("hook", premise)).strip()
    conflict = str(idea.get("conflict", "Masalah muncul")).strip()
    twist = str(idea.get("twist", "Kejadian berakhir dengan kejutan")).strip()
    series = str(idea.get("series_potential", "Cerita ini bisa berlanjut di episode berikutnya.")).strip()
    selected_hook_text = str(hook.get("hook", seed_hook)).strip()
    selected_hook_visual = str(hook.get("visual", seed_hook)).strip()
    is_local = cfg.get("mode") == "Indonesia Lokal"

    if is_local:
        beats = [
            {"start":0,"end":1,"purpose":"HOOK","visual":selected_hook_visual,
             "action":"Buka tepat pada kejadian paling aneh dari ide terpilih; tanpa intro.",
             "dialogue":selected_hook_text,"sound":"SFX singkat yang menegaskan kejadian, lalu jeda untuk reaksi."},
            {"start":1,"end":3,"purpose":"CONTEXT","visual":premise or seed_hook,
             "action":f"Tunjukkan situasi utama dari judul: {title}. Penonton langsung paham siapa, di mana, dan masalahnya.",
             "dialogue":f"Karakter bereaksi terhadap situasi: {premise}","sound":"Ambience lokasi yang sesuai; dialog tetap jelas."},
            {"start":3,"end":6,"purpose":"CONFLICT","visual":conflict,
             "action":f"Perlihatkan konflik utama secara konkret: {conflict}. Buat masalah makin sulit, bukan mengulang shot awal.",
             "dialogue":conflict,"sound":"SFX mengikuti aksi konflik."},
            {"start":6,"end":8,"purpose":"ESCALATION","visual":twist,
             "action":f"Bangun kejutan berdasarkan payoff ide: {twist}. Gunakan ekspresi dan properti yang terlihat jelas.",
             "dialogue":twist,"sound":"Musik naik sebentar lalu berhenti tepat sebelum punchline."},
            {"start":8,"end":10,"purpose":"PAYOFF + CTA","visual":f"Reaksi close-up setelah twist: {twist}",
             "action":"Sampaikan punchline dan CTA wajib secara lucu: sebut like, subscribe channel, lalu pemicu menonton ulang yang terkait dengan twist.",
             "dialogue":f"{twist} — Kalau twist ini bikin kamu ketawa, pencet LIKE dan SUBSCRIBE channel ini; tonton ulang, petunjuknya ada di {title.lower()} dari awal!",
             "sound":"Sting komedi singkat, tahan reaksi, lalu potong untuk loop."}
        ]
        cta = f"Kalau twist {title.lower()} bikin kamu ketawa, pencet LIKE dan SUBSCRIBE channel ini. Tonton ulang—petunjuknya muncul dari awal!"
    else:
        beats = [
            {"start":0,"end":1,"purpose":"HOOK","visual":selected_hook_visual,
             "action":"Open on the selected concept's most surprising visual; no intro.",
             "dialogue":selected_hook_text,"sound":"A sharp, relevant sound cue, then a beat of silence."},
            {"start":1,"end":3,"purpose":"CONTEXT","visual":premise or seed_hook,
             "action":f"Establish the exact situation in '{title}' clearly.",
             "dialogue":premise,"sound":"Location ambience; keep dialogue clear."},
            {"start":3,"end":6,"purpose":"CONFLICT","visual":conflict,
             "action":f"Show the selected idea's central problem: {conflict}. Escalate visibly.",
             "dialogue":conflict,"sound":"Sound effects tied to the action."},
            {"start":6,"end":8,"purpose":"ESCALATION","visual":twist,
             "action":f"Set up the actual payoff: {twist}.",
             "dialogue":twist,"sound":"Brief rising cue, cut before the punchline."},
            {"start":8,"end":10,"purpose":"PAYOFF + CTA","visual":f"Close-up reaction to: {twist}",
             "action":"Deliver the punchline and required explicit LIKE + SUBSCRIBE invitation as part of the character joke; add a replay cue.",
             "dialogue":f"{twist} — Hit LIKE and SUBSCRIBE to this channel if that twist got you; rewatch it—the clue was there from the start!",
             "sound":"Short comedic sting, hold the reaction, then cut for a possible loop."}
        ]
        cta = f"If the twist in {title} got you, hit LIKE and SUBSCRIBE to this channel; rewatch it—the clue was there from the start!"

    # Stretch the demo timeline to the selected total duration without changing story order.
    total_duration = int(cfg.get("duration", 10))
    base_duration = 10
    for beat in beats:
        beat["start"] = round(beat["start"] * total_duration / base_duration)
        beat["end"] = round(beat["end"] * total_duration / base_duration)
        if beat["end"] <= beat["start"]:
            beat["end"] = beat["start"] + 1

    return {
        "title": title,
        "logline": premise,
        "hook": {"visual": selected_hook_visual, "dialogue": selected_hook_text, "duration_seconds": 1},
        "beats": beats,
        "punchline": twist,
        "cta": cta,
        "return_potential": series,
        "continuity_notes": [
            f"Keep the same character and visual identity: {cfg.get('character', 'selected character')}.",
            f"Keep the story in the selected setting: {cfg.get('setting', 'selected setting')}.",
            f"Every shot must serve the selected title '{title}' and its premise: {premise}.",
            "Do not introduce unrelated characters, props, or jokes. End on a reaction or pose that can loop to the opening."
        ]
    }

def enforce_cta_requirements(story, cfg):
    """Ensure generated package explicitly asks for subscribe + like and invites replay."""
    title = str(story.get("title", "cerita ini"))
    cta = str(story.get("cta", "")).strip()
    text_blob = cta.lower()
    has_sub = any(term in text_blob for term in ["subscribe", "berlangganan", "subscribe channel", "ikuti channel"])
    has_like = any(term in text_blob for term in ["like", "suka", "tombol jempol"])
    has_replay = any(term in text_blob for term in ["tonton ulang", "ulang", "rewatch", "replay", "watch again"])
    is_local = cfg.get("mode") == "Indonesia Lokal"
    if not (has_sub and has_like and has_replay):
        if is_local:
            fallback = f"Kalau twist {title.lower()} bikin kamu ketawa, pencet LIKE dan SUBSCRIBE channel ini. Tonton ulang—petunjuknya muncul dari awal!"
        else:
            fallback = f"If the twist in {title} got you, hit LIKE and SUBSCRIBE to this channel. Rewatch it—the clue was there from the start!"
        cta = (cta + " " + fallback).strip() if cta else fallback
        story["cta"] = cta
    beats = story.get("beats", [])
    if beats:
        last = beats[-1]
        dialogue = str(last.get("dialogue", ""))
        low_dialogue = dialogue.lower()
        dialogue_has_sub = any(term in low_dialogue for term in ["subscribe", "berlangganan", "ikuti channel"])
        dialogue_has_like = any(term in low_dialogue for term in ["like", "suka", "tombol jempol"])
        dialogue_has_replay = any(term in low_dialogue for term in ["tonton ulang", "ulang", "rewatch", "replay", "watch again"])
        if not (dialogue_has_sub and dialogue_has_like and dialogue_has_replay):
            last["dialogue"] = (dialogue + " " + cta).strip()
        last["purpose"] = "PAYOFF + CTA WAJIB + LOOP"
    story.setdefault("return_potential", "Tonton ulang untuk menangkap petunjuk yang muncul pada adegan pembuka.")
    return story


def build_flow_prompts(cfg, story):
    """Split a story timeline into consecutive Flow segments of at most 10 seconds."""
    beats = story.get("beats", [])
    total = int(cfg.get("duration", 10))
    chunks = []
    for start in range(0, total, 10):
        end = min(start + 10, total)
        segment_beats = [b for b in beats if int(b.get("start", 0)) < end and int(b.get("end", 0)) > start]
        beat_text = []
        for b in segment_beats:
            beat_text.append(
                f"{b.get('start')}–{b.get('end')}s | {b.get('purpose')}\n"
                f"Visual: {b.get('visual')}\nAction: {b.get('action')}\n"
                f"Dialogue: {b.get('dialogue')}\nSound: {b.get('sound')}"
            )
        prompt = f"""GOOGLE FLOW VIDEO PROMPT — SEGMENT {len(chunks)+1}
Duration: {end-start} seconds. Timeline position: {start}–{end} seconds of a {total}-second video. Aspect ratio: 9:16 vertical.
Title: {story.get('title')}
Character: {cfg['character']}
Setting: {cfg['setting']}
Visual direction: realistic cinematic live-action / photorealistic CGI, detailed natural materials,
physically plausible lighting, sharp focus, believable motion, expressive but non-cartoon performance.
{realism_rules(cfg['mode'])}

TIMELINE FOR THIS SEGMENT:
{chr(10).join(beat_text)}

CONTINUITY:
{chr(10).join('- '+str(n) for n in story.get('continuity_notes', []))}
Keep the character design, proportions, clothing/accessories, location, props, and lighting consistent.
This segment must depict only events from {start} to {end} seconds. Segment 2 onward continues the previous segment without restarting.
Use readable actions and one clear focal point at a time. Dialogue should be spoken naturally in the language selected for this channel.
Do not add extra characters, dialogue, captions, logos, watermarks, or unrelated events. End on a stable frame that can connect to the next segment."""
        chunks.append({"segment": len(chunks)+1, "start": start, "end": end, "prompt": prompt})
    return chunks

def embed_broll_into_flow(flow_prompts, broll, story):
    """Attach story-matched B-roll as timed cutaway instructions inside each Flow prompt."""
    if not flow_prompts or not broll:
        return flow_prompts
    total = max(1, max(int(seg.get("end", 0)) for seg in flow_prompts))
    shots = []
    for shot in broll:
        try:
            shots.append(shot)
        except Exception:
            continue
    for idx, seg in enumerate(flow_prompts):
        start, end = int(seg.get("start", 0)), int(seg.get("end", 0))
        # Spread the five B-roll beats across the full timeline; each segment receives
        # only shots that fall in its time window (with a safe proportional fallback).
        chosen = []
        for j, shot in enumerate(shots):
            shot_time = min(total - 1, int((j + 0.5) * total / max(1, len(shots))))
            if start <= shot_time < end:
                chosen.append((j, shot))
        if not chosen and shots:
            nearest = min(range(len(shots)), key=lambda j: abs(min(total - 1, int((j + 0.5) * total / len(shots))) - (start + end) / 2))
            chosen = [(nearest, shots[nearest])]
        broll_lines = []
        for j, shot in chosen:
            shot_start = min(end - 1, max(start, int((j + 0.5) * total / max(1, len(shots)))))
            shot_end = min(end, shot_start + max(1, int(shot.get("duration_seconds", 2))))
            broll_lines.append(
                f"CUTAWAY {shot_start}–{shot_end}s ({shot.get('type', 'B-roll')}): "
                f"{shot.get('prompt', '')} Purpose: {shot.get('purpose', '')}."
            )
        segment_prompt = seg.get("prompt", "")
        segment_prompt += "\n\nINTEGRATED B-ROLL / CUTAWAYS — INCLUDE THESE WITHIN THIS SAME VIDEO SEGMENT; do not make a separate unrelated montage:\n"
        segment_prompt += "\n".join("- " + line for line in broll_lines)
        segment_prompt += "\nEDITING RHYTHM: use these as brief 1–2 second cutaways at the specified points, then return to the main action. Preserve exact character, prop, location, lighting, and story continuity. Keep the hook and dialogue clear; do not cover key dialogue with cutaways."
        seg["prompt"] = segment_prompt
        seg["integrated_broll"] = [shot for _, shot in chosen]
    return flow_prompts


def make_broll_prompt(cfg, story):
    prompt = f"""
Create exactly 5 supporting B-roll shot prompts for this video.
Return valid JSON only: {{"broll":[{{"type":"...","duration_seconds":2,"prompt":"...","purpose":"..."}},...]}}
Story title: {story.get('title')}
Story: {story.get('logline')}
Character: {cfg['character']}; location: {cfg['setting']}; channel: {cfg['mode']}.
Use these types once each: establishing shot, character reaction, important prop close-up,
conflict escalation, punchline reaction.
Each shot must support the actual story, not invent a different plot. Keep character identity and props consistent.
Photorealistic realistic cinematic look. Not cartoon, not anime, not illustration, not plastic toy.
Vertical 9:16, sharp focus, no text, no logo, no watermark.
"""
    return prompt

def demo_broll(cfg, story):
    title = story.get("title", "Selected story")
    return {"broll": [
        {"type":"Establishing shot","duration_seconds":2,"purpose":"Establish location and atmosphere.","prompt":f"Realistic cinematic vertical wide shot of {cfg['setting']}, consistent with '{title}', natural detailed textures, sharp subject focus, no text."},
        {"type":"Character reaction","duration_seconds":2,"purpose":"Show the character's emotional response.","prompt":f"Photorealistic close-up of {cfg['character']} reacting to the main problem in '{title}', expressive but realistic, same character design, no cartoon look."},
        {"type":"Important prop close-up","duration_seconds":2,"purpose":"Make the key story object instantly readable.","prompt":f"Realistic macro close-up of the key prop from '{title}', detailed material, dramatic but natural cinematic lighting, consistent continuity, no text."},
        {"type":"Conflict escalation","duration_seconds":2,"purpose":"Visually communicate the problem getting worse.","prompt":f"Realistic medium shot showing the central conflict escalating in '{title}', same location and character, physically plausible movement, crisp focus."},
        {"type":"Punchline reaction","duration_seconds":2,"purpose":"Capture the final deadpan or surprised reaction.","prompt":f"Photorealistic reaction shot of {cfg['character']} immediately after the punchline of '{title}', hold the expression, consistent lighting and appearance, no captions."}
    ]}

# ----------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.header("⚙️ Pengaturan Studio")
    api_key = st.text_input("ClarioHub API Key", type="password", help="Masukkan API key ClarioHub (format biasanya sk-clario-...). Jangan bagikan key.")
    model_options = ["clario/deepseek-v4-flash", "clario/deepseek-v4-pro", "clario/deepseek-v4.1-flash", "clario/glm-5.3-flash", "clario/glm-5.3", "clario/gemini-3.7-flash", "clario/gpt-5.6-sol", "clario/hy3", "clario/hy4-preview", "clario/minimax-m3", "clario/opus-5"]
    model = st.selectbox("Model ClarioHub", model_options, index=0, help="Gunakan ID model yang tersedia untuk key standard di katalog ClarioHub.")
    st.caption("API: https://clariohub.id/v1/chat/completions · Tanpa key, aplikasi memakai mode demo.")
    st.divider()
    st.selectbox("Mode channel", ["Global Skeleton", "Indonesia Lokal", "Lokal + Global"], key="mode")
    themes = {
        "Global Skeleton": ["Absurd Comedy", "Horror Comedy", "Gym & Fitness", "Relationship Comedy", "Work & Money", "Gaming Comedy", "Survival Comedy", "Sci-Fi Comedy", "Everyday Life"],
        "Indonesia Lokal": ["Komedi Horor", "Kehidupan Anak Kos", "Komedi Tongkrongan", "Keluarga", "Pekerjaan & Uang", "Mitos Lokal", "Kehidupan Sehari-hari"],
        "Lokal + Global": ["Absurd Comedy", "Komedi Horor", "Everyday Life", "Work & Money", "Relationship Comedy", "Kehidupan Anak Kos", "Survival Comedy"]
    }
    subthemes = {
        "Global Skeleton": {
            "Absurd Comedy": ["Everyday disaster", "Impossible job interview", "Broken bones problem", "Awkward public moment"],
            "Horror Comedy": ["Haunted apartment", "Ghost roommate", "Cursed elevator", "Monster with a day job"],
            "Gym & Fitness": ["First day at gym", "Broken workout equipment", "Overconfident trainer", "Fitness challenge disaster"],
            "Relationship Comedy": ["Awkward first date", "Jealous skeleton", "Text message misunderstanding", "Breakup gone wrong"],
            "Work & Money": ["First day at work", "Rent is due", "Boss from hell", "Broke before payday"],
            "Gaming Comedy": ["Rage quit", "Noob versus pro", "Game bug in real life", "Impossible boss fight"],
            "Survival Comedy": ["Lost in the woods", "Survive one night", "Disaster camping trip", "Wrong survival tip"],
            "Sci-Fi Comedy": ["Alien roommate", "Time travel mistake", "Robot takes over chores", "Portal delivery disaster"],
            "Everyday Life": ["Morning disaster", "Grocery store chaos", "Public transport problem", "Neighbor drama"]
        },
        "Indonesia Lokal": {
            "Komedi Horor": ["Pocong nagih uang kos", "Kuntilanak salah kamar", "Hantu anak kos", "Jin jadi satpam", "Hantu minta subscribe"],
            "Kehidupan Anak Kos": ["Uang kos habis", "Teman kos pelit", "Listrik mati tengah malam", "Mie instan terakhir", "Pemilik kos menagih"],
            "Komedi Tongkrongan": ["Teman sok kaya", "Traktiran palsu", "Utang warung", "Salah kirim chat", "Teman datang cuma saat butuh"],
            "Keluarga": ["Anak ketahuan bohong", "Drama uang belanja", "Ayah salah paham", "Ibu punya jurus rahasia", "Rebutan remote TV"],
            "Pekerjaan & Uang": ["Gaji baru masuk langsung habis", "Bos banyak mau", "Telat gajian", "Pelanggan banyak tingkah", "Cari kerja malah apes"],
            "Mitos Lokal": ["Penunggu pohon ikut ronda", "Jin salah alamat", "Benda keramat hilang", "Suara misterius dari dapur", "Hantu takut manusia"],
            "Kehidupan Sehari-hari": ["Salah naik kendaraan", "Antrean tidak bergerak", "Paket tertukar", "Tetangga kepo", "Warung kehabisan kembalian"]
        },
        "Lokal + Global": {
            "Absurd Comedy": ["Everyday disaster", "Impossible situation", "Awkward public moment"],
            "Komedi Horor": ["Pocong nagih uang kos", "Hantu minta subscribe", "Kuntilanak salah kamar"],
            "Everyday Life": ["Morning disaster", "Grocery store chaos", "Neighbor drama"],
            "Work & Money": ["First day at work", "Rent is due", "Broke before payday"],
            "Relationship Comedy": ["Awkward first date", "Text message misunderstanding", "Breakup gone wrong"],
            "Kehidupan Anak Kos": ["Uang kos habis", "Teman kos pelit", "Listrik mati tengah malam"],
            "Survival Comedy": ["Lost in the woods", "Disaster camping trip", "Wrong survival tip"]
        }
    }
    mode = st.session_state.mode
    theme_options = themes[mode]
    if st.session_state.get("theme") not in theme_options:
        st.session_state.theme = theme_options[0]
    st.selectbox("Tema", theme_options, key="theme")
    active_subthemes = subthemes[mode].get(st.session_state.theme, ["Kejadian absurd", "Masalah sehari-hari"])
    custom_option = "✍️ Tulis subtema sendiri..."
    subtheme_options = active_subthemes + [custom_option]

    # Custom text has its own state. Never copy the current subtheme back into
    # the text input on every Streamlit rerun, or the user's typing gets overwritten.
    if "subtheme_custom_value" not in st.session_state:
        st.session_state.subtheme_custom_value = ""
    if st.session_state.get("subtheme_choice") not in subtheme_options:
        previous_subtheme = st.session_state.get("subtheme", "")
        if previous_subtheme in active_subthemes:
            st.session_state.subtheme_choice = previous_subtheme
        else:
            st.session_state.subtheme_choice = active_subthemes[0]

    chosen_subtheme = st.selectbox(
        "Subtema", subtheme_options, key="subtheme_choice",
        help="Pilih subtema yang tersedia atau pilih 'Tulis subtema sendiri'."
    )
    if chosen_subtheme == custom_option:
        custom_subtheme = st.text_area(
            "Tulis subtema sendiri",
            key="subtheme_custom_value",
            placeholder="Contoh: Pocong, kuntilanak, dan tuyul pergi ke pasar malam untuk naik bom-bom car",
            height=100,
            help="Teks ini akan dipakai sebagai inti cerita. Setelah mengetik, lanjutkan ke tombol Generate Ide."
        ).strip()
        st.session_state.subtheme = custom_subtheme
        if custom_subtheme:
            st.caption("✅ Subtema khusus tersimpan untuk sesi ini.")
        else:
            st.caption("Tulis subtema di atas sebelum menekan Generate Ide.")
    else:
        st.session_state.subtheme = chosen_subtheme

    if mode == "Indonesia Lokal":
        character_options = ["Pocong", "Kuntilanak", "Genderuwo", "Jin", "Manusia + Hantu Lokal"]
        base_setting_options = ["Pasar malam", "Taman hiburan", "Kos-kosan Indonesia", "Warung pinggir jalan", "Kampung malam hari", "Rumah tua Indonesia", "Pos ronda", "Kantor Indonesia", "Sekolah", "Pantai", "Hutan"]
        audience_options = ["Umum", "Remaja dan dewasa", "Ramah keluarga"]
        humor_options = ["Komedi absurd cepat", "Komedi deadpan", "Komedi horor", "Komedi keseharian"]
    elif mode == "Global Skeleton":
        character_options = ["Overconfident Skeleton", "Realistic Skeleton", "Ghost roommate", "Human + supernatural character"]
        base_setting_options = ["Amusement park", "Night market", "Small apartment", "Modern gym", "Office", "Supermarket", "Suburban street", "Hospital", "Beach", "Forest"]
        audience_options = ["General audience", "Teens and adults", "Family-friendly"]
        humor_options = ["Absurd, fast-paced, visual", "Deadpan comedy", "Horror-comedy", "Relatable everyday comedy"]
    else:
        character_options = ["Realistic Skeleton", "Overconfident Skeleton", "Pocong", "Kuntilanak", "Human + supernatural character"]
        base_setting_options = ["Pasar malam", "Night market", "Amusement park", "Apartment", "Kos-kosan Indonesia", "Warung", "Office", "Old house", "Beach", "Forest"]
        audience_options = ["General audience", "Remaja dan dewasa", "Family-friendly"]
        humor_options = ["Absurd comedy", "Komedi horor", "Deadpan comedy", "Relatable everyday comedy"]

    # Add context-matched locations when the custom subtheme mentions a specific place.
    subtheme_text = str(st.session_state.get("subtheme", "")).lower()
    contextual_locations = []
    context_rules = [
        (("pasar malam", "bom-bom", "bombom", "komidi putar", "bianglala"), "Pasar malam" if mode != "Global Skeleton" else "Night market"),
        (("pantai", "laut", "ombak"), "Pantai" if mode != "Global Skeleton" else "Beach"),
        (("hutan", "pohon", "kemah", "camping"), "Hutan" if mode != "Global Skeleton" else "Forest"),
        (("warung", "nasi goreng", "arom manis", "arum manis"), "Warung pinggir jalan" if mode == "Indonesia Lokal" else ("Warung" if mode == "Lokal + Global" else "Food stall")),
        (("kos", "uang kos", "kamar kos"), "Kos-kosan Indonesia" if mode != "Global Skeleton" else "Small apartment"),
        (("kantor", "bos", "rapat"), "Kantor Indonesia" if mode == "Indonesia Lokal" else ("Office" if mode == "Global Skeleton" else "Office")),
    ]
    for keywords, location in context_rules:
        if any(word in subtheme_text for word in keywords):
            contextual_locations.append(location)
    setting_options = list(dict.fromkeys(contextual_locations + base_setting_options))
    custom_location_option = "✍️ Tulis lokasi sendiri..."
    setting_options.append(custom_location_option)

    # When the subtheme changes, suggest a matching location rather than keeping an unrelated default.
    previous_setting_subtheme = st.session_state.get("last_setting_subtheme")
    if previous_setting_subtheme != st.session_state.get("subtheme") and contextual_locations:
        st.session_state.setting_choice = contextual_locations[0]
        st.session_state.setting = contextual_locations[0]
    st.session_state.last_setting_subtheme = st.session_state.get("subtheme", "")

    if st.session_state.get("character") not in character_options:
        st.session_state.character = character_options[0]
    if st.session_state.get("setting_choice") not in setting_options:
        old_setting = st.session_state.get("setting", "")
        st.session_state.setting_choice = old_setting if old_setting in setting_options else (contextual_locations[0] if contextual_locations else base_setting_options[0])
    if "setting_custom_value" not in st.session_state:
        st.session_state.setting_custom_value = ""

    st.selectbox("Karakter utama", character_options, key="character")
    chosen_setting = st.selectbox(
        "Lokasi utama", setting_options, key="setting_choice",
        help="Lokasi otomatis menyarankan tempat yang cocok dengan subtema. Pilih 'Tulis lokasi sendiri' untuk tempat lain."
    )
    if chosen_setting == custom_location_option:
        custom_setting = st.text_input(
            "Tulis lokasi sendiri", key="setting_custom_value",
            placeholder="Contoh: pasar malam yang ramai dengan wahana bom-bom car",
            help="Lokasi ini akan dipakai sebagai latar utama prompt cerita dan visual."
        ).strip()
        st.session_state.setting = custom_setting or "Lokasi sesuai subtema (belum diisi)"
        if custom_setting:
            st.caption("✅ Lokasi khusus tersimpan untuk sesi ini.")
        else:
            st.caption("Tulis lokasi yang sesuai sebelum menekan Generate.")
    else:
        st.session_state.setting = chosen_setting
    st.selectbox("Target penonton", audience_options, key="audience")
    st.selectbox("Gaya humor", humor_options, key="humor")
    st.selectbox("Tujuan video", ["Subscriber growth", "Views / reach", "Comments / discussion", "Shares", "Return viewers / series"], key="goal")
    st.selectbox("Durasi total (detik)", [10, 15, 20, 30, 40, 60], key="duration")
    st.selectbox("Gaya visual", ["Photorealistic live-action", "Realistic cinematic", "Realistic cinematic CGI"], key="style")
    st.caption("Pilih subtema siap pakai atau tulis subtema sendiri. Visual video diarahkan realistis — bukan kartun.")

ensure_current()
cfg = current_config()

# ----------------------------- HEADER -----------------------------
st.markdown(f"""
<div class="hero">
  <h1>💀 {APP_NAME}</h1>
  <p><b>KLIK → BERTAHAN → KEMBALI</b> · Atur sekali, pilih judul, lalu hasilkan paket konten lengkap.</p>
  <span class="pill">Hook otomatis</span><span class="pill">CTA menyatu dengan punchline</span>
  <span class="pill">Prompt Flow</span><span class="pill">B-roll otomatis</span>
</div>
""", unsafe_allow_html=True)

st.caption("Alur singkat: atur mode, tema, subtema, karakter, lokasi, dan durasi di panel pengaturan → Generate Ide → pilih judul → Generate Paket Lengkap.")
if not api_key.strip():
    st.warning("MODE DEMO AKTIF: tanpa API key ClarioHub, aplikasi tidak memanggil AI. Ide demo kini mengikuti subtema/karakter/lokasi yang dipilih, tetapi untuk ide dan cerita yang benar-benar baru setiap kali generate, isi API key ClarioHub di panel pengaturan.")

# ----------------------------- STEP 1: IDEAS -----------------------------
st.header("1. 💡 Pilih ide video")
col_a, col_b = st.columns([1, 3])
with col_a:
    idea_count = st.selectbox("Jumlah ide", [5, 8, 10], index=0)
with col_b:
    if st.button("🚀 Generate Ide", type="primary", use_container_width=True):
        clear_from("ideas")
        with st.spinner("Mencari ide yang cocok dengan tema dan subtema..."):
            try:
                result = ai_or_demo(make_ideas_prompt(cfg, idea_count), api_key, model,
                                    lambda: demo_ideas(cfg, idea_count), temperature=0.9)
                st.session_state.ideas = result.get("ideas", [])
                st.session_state.selected_idea = {}
                st.session_state.selected_title = ""
                st.session_state.chosen_idea_title = str(st.session_state.ideas[0].get("title", "")) if st.session_state.ideas else ""
                st.session_state.story = {}
                st.session_state.flow_prompts = []
                st.session_state.broll = []
                if not st.session_state.ideas:
                    raise ValueError("Ide tidak berhasil dibuat. Coba lagi.")
            except Exception as e:
                st.error(str(e))

if st.session_state.ideas:
    titles = [str(i.get("title", f"Ide {n+1}")) for n, i in enumerate(st.session_state.ideas)]
    selected_title = st.selectbox("Pilih judul yang ingin dikembangkan", titles, key="chosen_idea_title")
    selected_idea = next((i for i in st.session_state.ideas if str(i.get("title", "")) == selected_title), st.session_state.ideas[0])
    st.session_state.selected_idea = selected_idea
    st.session_state.selected_title = selected_title
    st.markdown(f"### {selected_title}")
    st.write(selected_idea.get("premise", ""))
    with st.expander("Lihat konflik, twist, dan potensi serial"):
        st.markdown("**Konflik**")
        st.write(selected_idea.get("conflict", ""))
        st.markdown("**Twist / payoff**")
        st.write(selected_idea.get("twist", ""))
        st.markdown("**Potensi serial**")
        st.write(selected_idea.get("series_potential", ""))

    # One action generates the full production package; hook selection is automatic.
    if st.button("🎬 GENERATE PAKET LENGKAP", type="primary", use_container_width=True):
        st.session_state.story = {}
        st.session_state.flow_prompts = []
        st.session_state.broll = []
        st.session_state.hooks = []
        st.session_state.selected_hook = ""
        try:
            with st.spinner("1/4 Membuat hook terkuat yang sesuai judul..."):
                hook_result = ai_or_demo(
                    make_hooks_prompt(cfg, selected_idea), api_key, model,
                    lambda: demo_hooks(cfg, selected_idea), temperature=0.9)
                hooks = hook_result.get("hooks", [])
                if not hooks:
                    raise ValueError("Hook otomatis tidak berhasil dibuat.")
                # First hook is required to be strongest by prompt; no manual hook selection.
                hook_obj = hooks[0]
                st.session_state.hooks = hooks
                st.session_state.selected_hook = hook_obj.get("hook", "")
            with st.spinner("2/4 Merangkai cerita, twist, CTA, dan loop... "):
                story = ai_or_demo(
                    make_story_prompt(cfg, selected_idea, hook_obj), api_key, model,
                    lambda: demo_story(cfg, selected_idea, hook_obj), temperature=0.85)
                story["title"] = selected_idea.get("title", selected_title)
                story["hook"] = story.get("hook") or {
                    "visual": hook_obj.get("visual", ""),
                    "dialogue": hook_obj.get("hook", ""),
                    "duration_seconds": 2,
                }
                story["automatic_hook_strength"] = hook_obj.get("strength", "Hook dipilih otomatis dari ide terpilih.")
                story = enforce_cta_requirements(story, cfg)
                st.session_state.story = story
            with st.spinner("3/4 Menyiapkan prompt Google Flow per segmen... "):
                if api_key:
                    flow_request = f"""Return valid JSON only: {{"segments":[{{"segment":1,"start":0,"end":10,"prompt":"..."}}]}}.
Create all video prompts for this exact story, total target duration {cfg['duration']} seconds. Split into continuous segments no longer than 10 seconds each; the final segment may be shorter. Segment timeline must cover 0 through {cfg['duration']} with no gaps or overlap. Each segment prompt should only depict events in its timeline. Keep the same characters, props, location, and visual identity; segment 2 onward continues the previous segment, never restarts. Selected title: {selected_idea.get('title')}. Config: {json.dumps(cfg, ensure_ascii=False)}. Story: {json.dumps(story, ensure_ascii=False)}. {realism_rules(cfg['mode'])}"""
                    flow_result = clariohub_generate(flow_request, api_key, model, 0.6)
                    segments = flow_result.get("segments", [])
                    clean = []
                    cursor = 0
                    segment_size = 10
                    for idx, seg in enumerate(segments):
                        start_sec = max(cursor, int(seg.get("start", cursor)))
                        end_sec = min(cfg["duration"], int(seg.get("end", min(start_sec + segment_size, cfg["duration"]))))
                        if end_sec <= start_sec:
                            end_sec = min(start_sec + segment_size, cfg["duration"])
                        if end_sec <= start_sec:
                            continue
                        clean.append({"segment": len(clean)+1, "start": start_sec, "end": end_sec, "prompt": seg.get("prompt", "")})
                        cursor = end_sec
                        if cursor >= cfg["duration"]:
                            break
                    # If model returns incomplete coverage, use deterministic prompts for the uncovered timeline.
                    if not clean or cursor < cfg["duration"]:
                        clean = build_flow_prompts(cfg, story)
                    st.session_state.flow_prompts = clean
                else:
                    st.session_state.flow_prompts = build_flow_prompts(cfg, story)
            with st.spinner("4/4 Membuat B-roll yang cocok dengan cerita... "):
                if api_key:
                    broll_result = clariohub_generate(make_broll_prompt(cfg, story), api_key, model, 0.7)
                else:
                    broll_result = demo_broll(cfg, story)
                st.session_state.broll = broll_result.get("broll", [])
                # B-roll is automatically embedded into the corresponding Flow prompts,
                # while remaining separately visible for optional manual editing.
                st.session_state.flow_prompts = embed_broll_into_flow(
                    st.session_state.flow_prompts, st.session_state.broll, story
                )
            st.success("Paket selesai: hook, CTA, prompt Flow, dan B-roll terintegrasi otomatis sesuai judul serta cerita.")
        except Exception as e:
            st.error(f"Paket belum selesai: {e}")

# ----------------------------- FULL PACKAGE OUTPUT -----------------------------
if st.session_state.story:
    story = st.session_state.story
    st.divider()
    st.header("2. 🎬 Hasil paket lengkap")
    st.subheader(story.get("title", "Cerita"))
    st.markdown("#### 🧲 KLIK — Hook otomatis")
    hook_data = story.get("hook", {})
    st.success(hook_data.get("dialogue", st.session_state.selected_hook))
    if hook_data.get("visual"):
        st.write("**Visual pembuka:** " + str(hook_data.get("visual")))
    if story.get("automatic_hook_strength"):
        st.caption(story["automatic_hook_strength"])

    st.markdown("#### ⏳ BERTAHAN — Alur cerita")
    st.write(story.get("logline", ""))
    beats = story.get("beats", [])
    if beats:
        st.dataframe([{
            "Waktu": f"{b.get('start','?')}–{b.get('end','?')}s",
            "Tahap": b.get("purpose", ""),
            "Visual": b.get("visual", ""),
            "Aksi": b.get("action", ""),
            "Dialog": b.get("dialogue", ""),
        } for b in beats], use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 💥 Punchline")
        st.write(story.get("punchline", ""))
    with c2:
        st.markdown("#### 🧲 CTA otomatis — SUBSCRIBE + LIKE + TONTON ULANG")
        st.write(story.get("cta", ""))
    st.markdown("#### 🔁 KEMBALI — Alasan menonton ulang")
    st.write(story.get("return_potential", "Akhiri dengan pose/gerakan yang menyambung secara alami ke awal."))

    with st.expander("🎥 Prompt Google Flow + B-roll terintegrasi", expanded=True):
        for seg in st.session_state.flow_prompts:
            st.markdown(f"**SEGMENT {seg['segment']} · {seg['start']}–{seg['end']} detik**")
            st.code(seg["prompt"], language="text")
            st.download_button(f"⬇️ Download segmen {seg['segment']}", seg["prompt"],
                               file_name=f"flow_prompt_{seg['segment']:02d}.txt", mime="text/plain",
                               key=f"download_flow_{seg['segment']}")
    with st.expander("🎞️ B-roll otomatis", expanded=False):
        for i, shot in enumerate(st.session_state.broll):
            st.markdown(f"**{i+1}. {shot.get('type','B-roll')} · {shot.get('duration_seconds',2)} detik**")
            st.write(shot.get("purpose", ""))
            st.code(shot.get("prompt", ""), language="text")

    export_obj = {
        "app": APP_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config": cfg,
        "selected_idea": st.session_state.selected_idea,
        "selected_hook": story.get("hook", {}),
        "story": story,
        "flow_prompts": st.session_state.flow_prompts,
        "broll": st.session_state.broll,
    }
    export_json = json.dumps(export_obj, ensure_ascii=False, indent=2)
    export_text = [f"{APP_NAME} — {story.get('title','')}", "="*72,
                   f"MODE: {cfg['mode']} | THEME: {cfg['theme']} / {cfg['subtheme']}",
                   f"DURATION: {cfg['duration']} seconds", "", "STORY",
                   json.dumps(story, ensure_ascii=False, indent=2), "", "GOOGLE FLOW PROMPTS"]
    for seg in st.session_state.flow_prompts:
        export_text.append(f"\n--- SEGMENT {seg['segment']} ({seg['start']}–{seg['end']}s) ---\n{seg['prompt']}")
    export_text.extend(["", "B-ROLL", json.dumps(st.session_state.broll, ensure_ascii=False, indent=2)])
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📦 Download semua (TXT)", "\n".join(export_text),
                           file_name="cadas_resonance_output.txt", mime="text/plain", use_container_width=True)
    with col2:
        st.download_button("📁 Download project (JSON)", export_json,
                           file_name="cadas_resonance_project.json", mime="application/json", use_container_width=True)

with st.expander("⚙️ Petunjuk singkat"):
    st.write("1. Atur mode, tema, subtema, karakter, lokasi, durasi, dan visual di panel pengaturan.")
    st.write("2. Tekan **Generate Ide**, pilih judul, lalu tekan **Generate Paket Lengkap** satu kali.")
    st.write("3. Hook, cerita, CTA, prompt Flow, B-roll, dan file export dibuat otomatis.")
    st.caption("Tanpa ClarioHub API key, aplikasi menggunakan demo fallback; hasilnya bukan generasi AI langsung. API key dan kuota mengikuti penyedia layanan.")
