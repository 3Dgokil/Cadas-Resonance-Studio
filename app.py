# Cadas Resonance Studio — app.py
# Streamlit app for CLICK -> STAY -> RETURN content planning.
# Optional Gemini API integration. Without an API key, the app runs in demo mode.
# Run: pip install streamlit requests && streamlit run app.py

import json
import random
import re
import textwrap
from datetime import datetime

import requests
import streamlit as st

APP_NAME = "CADAS RESONANCE STUDIO"
DEFAULT_MODEL = "gemini-2.5-flash"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="💀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- UI STYLE -----------------------------
st.markdown("""
<style>
    .stApp { background:#f4f7fb; color:#202938; }
    [data-testid="stHeader"] { background:rgba(244,247,251,.96); }
    [data-testid="stSidebar"] { background:#ffffff; border-right:1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color:#263247; }
    .block-container { max-width:1180px; padding-top:1.2rem; padding-bottom:3rem; }
    .hero { padding:1.35rem 1.45rem; border-radius:18px;
        background:linear-gradient(120deg,#ffffff,#eaf3ff);
        border:1px solid #d8e6f8; margin-bottom:1rem;
        box-shadow:0 8px 24px rgba(40,80,140,.07); }
    .hero h1 { margin:0; font-size:2rem; color:#17345e; }
    .hero p { margin:.45rem 0 0; color:#52647d; }
    .pill { display:inline-block; padding:.22rem .55rem; margin:.15rem;
        border:1px solid #c8d8ed; border-radius:999px; color:#24466f;
        background:#f7fbff; font-size:.82rem; }
    .stage { border:1px solid #dbe5f1; background:#ffffff; border-radius:14px;
        padding:.9rem 1rem; min-height:100px; box-shadow:0 4px 14px rgba(30,60,100,.04); }
    .stage h4 { margin:0 0 .3rem; color:#1e4779; }
    .muted { color:#64748b; font-size:.9rem; }
    div.stButton > button { border-radius:10px; font-weight:650; min-height:2.7rem; }
    div.stButton > button[kind="primary"] { background:#1769d2; color:white; border-color:#1769d2; }
    div[data-testid="stAlert"] { border-radius:12px; }
    @media (max-width:700px) { .block-container { padding-left:1rem; padding-right:1rem; } .hero h1 {font-size:1.55rem;} }
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

def gemini_generate(prompt, api_key, model, temperature=0.85):
    if not api_key:
        raise RuntimeError("API key Gemini belum diisi. Isi di sidebar atau gunakan mode demo.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        },
        timeout=90,
    )
    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"Gemini API error ({response.status_code}): {detail}")
    data = response.json()
    try:
        return extract_json(data["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Respons Gemini kosong atau formatnya tidak dikenali.") from exc

def ai_or_demo(prompt, api_key, model, demo_fn, temperature=0.85):
    if api_key:
        return gemini_generate(prompt, api_key, model, temperature)
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
Each hook must be immediately understandable and visually filmable. Every concept needs a clear payoff.
{realism_rules(cfg['mode'])}
"""

def demo_ideas(cfg, count):
    if cfg["mode"] == "Indonesia Lokal":
        pool = [
            ("POCONG NAGIH UANG KOS", "Pocong datang menagih tunggakan kos seperti petugas administrasi.", "Pintu dibuka: pocong menyodorkan kuitansi bertuliskan TUNGGAKAN.", "Penghuni kos tidak punya uang dan mencoba kabur.", "Pocong mengeluarkan mesin EDC: bisa cicil 12 bulan.", "Episode berikutnya: pocong ikut kerja jadi debt collector."),
            ("KUNtilanak SALAH KAMAR", "Kuntilanak salah masuk kamar saat penghuni sedang rapat online.", "Rambut panjang muncul dari bawah meja saat rapat dimulai.", "Penghuni berusaha tetap profesional di depan bos.", "Bos ternyata juga hantu dan menegur karena terlambat.", "Serial kantor berhantu dengan aturan HR yang absurd."),
            ("HANTU GAK PUNYA CHANNEL", "Hantu menakut-nakuti orang, tetapi malah ditanya akun YouTube-nya.", "Hantu muncul dramatis; orang malah bertanya, 'Subscribe mana?'", "Hantu mencoba berbagai pose seram demi followers.", "Orang itu pergi setelah berkata, 'Nonton doang, gak subscribe.'", "Setiap episode hantu mencoba profesi baru untuk jadi viral."),
            ("WARUNG KHUSUS MAKHLUK HALUS", "Warung malam melayani pelanggan manusia dan hantu.", "Penjual menyodorkan menu ke pelanggan transparan.", "Hantu protes harga nasi goreng terlalu mahal.", "Penjual menjawab, 'Itu harga termasuk biaya penampakan.'", "Pelanggan supernatural dengan masalah sehari-hari."),
            ("SATPAM TAKUT HANTU", "Satpam harus menjaga gedung yang ternyata dihuni hantu penakut.", "Satpam melihat hantu dan justru hantu menjerit duluan.", "Keduanya saling menyuruh memeriksa suara dari lorong.", "Ternyata suara itu berasal dari alarm satpam sendiri.", "Duo satpam dan hantu memecahkan gangguan gedung.")
        ]
    else:
        pool = [
            ("MY DOCTOR SAID I HAVE TOO MANY BONES", "An overconfident skeleton gets a bizarre medical diagnosis.", "The doctor stares at the X-ray and slowly backs away.", "The skeleton insists he feels perfectly normal.", "The doctor says, 'You have one hundred percent of your bones. That's suspicious.'", "Recurring medical checkups with increasingly absurd diagnoses."),
            ("THE SKELETON'S FIRST DAY AT THE GYM", "A confident skeleton tries to impress a gym trainer.", "His arm pops off before the first rep.", "The trainer calls it a warm-up problem.", "The trainer adds more weight; the skeleton asks for a mechanic.", "Each episode features a new fitness trend gone wrong."),
            ("MY BOSS IS LITERALLY A MONSTER", "An employee discovers their boss is a monster but HR is worse.", "The boss's shadow grows across the entire office wall.", "The employee tries to resign politely.", "HR says the monster has already eaten the resignation form.", "Office survival stories with escalating workplace absurdity."),
            ("THE GHOST ASKED FOR A SUBSCRIPTION", "A ghost tries to scare a person who only cares about social media.", "A terrifying ghost appears; the person asks for its channel link.", "The ghost performs increasingly dramatic scares.", "The person leaves: 'I watched, but I didn't subscribe.'", "The ghost tries a new content strategy every episode."),
            ("THE WORST DELIVERY DRIVER EVER", "A skeleton delivers a pizza to the wrong dimension.", "The door opens onto a glowing portal and a customer holding a stopwatch.", "The skeleton tries to explain the delay.", "The customer tips him one bone and rates him one star.", "Deliveries to increasingly impossible locations.")
        ]
    random.shuffle(pool)
    ideas = []
    for item in pool[:count]:
        title, premise, hook, conflict, twist, series = item
        ideas.append({
            "title": title, "premise": premise, "hook": hook, "conflict": conflict,
            "twist": twist, "series_potential": series, "primary_goal": cfg["goal"]
        })
    return {"ideas": ideas}

def make_hooks_prompt(cfg, idea):
    return f"""
Generate exactly 3 alternative first-second hooks for this short-video concept.
Return JSON only: {{"hooks":[{{"hook":"...","visual":"...","curiosity":"...","strength":"..."}},...]}}
Concept title: {idea.get('title')}
Premise: {idea.get('premise')}
Conflict: {idea.get('conflict')}
Channel: {cfg['mode']}; theme: {cfg['theme']}; character: {cfg['character']}.
Language: {cfg['language']}
Hooks must be different approaches, immediately understandable, filmable, and not rely only on shouting.
Do not reveal the whole punchline in the hook.
{realism_rules(cfg['mode'])}
"""

def demo_hooks(cfg, idea):
    if cfg["mode"] == "Indonesia Lokal":
        return {"hooks": [
            {"hook": "POCONGNYA NAGIH KOS!", "visual": "Pintu terbuka; pocong menyodorkan kuitansi dengan wajah serius.", "curiosity": "Kenapa hantu punya kuitansi?", "strength": "Visual absurd + konflik langsung."},
            {"hook": "BANG, INI KOS ATAU ALAM GAIB?", "visual": "Penghuni membuka pintu dan melihat tiga pocong antre rapi.", "curiosity": "Apa yang mereka antrekan?", "strength": "Situasi mustahil yang mudah dipahami."},
            {"hook": "TUNGGAKANMU SUDAH DITEMUKAN!", "visual": "Pocong muncul dari balik pintu sambil menunjuk tagihan.", "curiosity": "Bagaimana penghuni akan membayar?", "strength": "Konflik langsung dan stakes jelas."}
        ]}
    return {"hooks": [
        {"hook": "BRO, WHY IS MY ARM OVER THERE?", "visual": "A realistic skeleton's arm falls off before the action starts.", "curiosity": "How will he handle the problem?", "strength": "Immediate visual surprise."},
        {"hook": "THE DOCTOR JUST QUIT.", "visual": "A doctor sees the X-ray and quietly removes their badge.", "curiosity": "What did the scan reveal?", "strength": "Curiosity gap with a clear reaction."},
        {"hook": "I PAID FOR THE PREMIUM BONES!", "visual": "The skeleton points angrily at a loose, rattling rib.", "curiosity": "Why are his bones failing?", "strength": "Unexpected dialogue and a visual prop."}
    ]}

def make_story_prompt(cfg, idea, hook):
    return f"""
Write a complete short-video story using the selected title and selected hook exactly as the source of truth.
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
 "cta":"short, natural, integrated with the joke or empty string",
 "return_potential":"...",
 "continuity_notes":["..."]
}}
Selected concept: {json.dumps(idea, ensure_ascii=False)}
Selected hook: {json.dumps(hook, ensure_ascii=False)}
Channel: {cfg['mode']}; theme: {cfg['theme']}/{cfg['subtheme']}; character: {cfg['character']};
setting: {cfg['setting']}; target: {cfg['audience']}; goal: {cfg['goal']}; humor: {cfg['humor']}.
Language: {cfg['language']}
Write a 10-second story that has a beginning, escalation, and satisfying punchline.
The CTA must be optional and short; prefer a joke-integrated CTA over generic "like and subscribe".
No filler, no long exposition, no unrelated jokes. The selected title must remain unchanged.
{realism_rules(cfg['mode'])}
"""

def demo_story(cfg, idea, hook):
    is_local = cfg["mode"] == "Indonesia Lokal"
    if is_local:
        beats = [
            {"start":0,"end":1,"purpose":"HOOK","visual":hook.get("visual", idea["hook"]),"action":"Pintu terbuka mendadak; karakter langsung memenuhi frame.","dialogue":hook.get("hook", idea["hook"]),"sound":"Ketukan keras, pintu berderit."},
            {"start":1,"end":3,"purpose":"CONTEXT","visual":"Medium shot penghuni kos yang kebingungan melihat kuitansi.","action":"Pocong menyodorkan tagihan dengan sikap administratif.","dialogue":"“Tunggakan kos tiga bulan.”","sound":"Musik tegang pendek."},
            {"start":3,"end":6,"purpose":"CONFLICT","visual":"Close-up penghuni merogoh kantong kosong.","action":"Penghuni membalik kantong; hanya debu yang jatuh.","dialogue":"“Bang, saya juga belum dibayar.”","sound":"Suara debu jatuh, hening komedi."},
            {"start":6,"end":8,"purpose":"ESCALATION","visual":"Pocong mengeluarkan mesin EDC dari balik kain kafan.","action":"Pocong menggesek kartu dengan wajah serius.","dialogue":"“Bisa cicil dua belas bulan.”","sound":"Beep mesin pembayaran."},
            {"start":8,"end":10,"purpose":"PAYOFF","visual":"Penghuni menatap kamera; di belakangnya tiga pocong sudah antre.","action":"Pocong pertama menunjuk antrean panjang.","dialogue":"“Yang berikutnya, siapin uang keamanan alam gaib!”","sound":"Bunyi antrean, sting komedi."}
        ]
        punchline = "Pocong menawarkan cicilan dan ternyata punya antrean pelanggan."
        cta = "Kalau masih nonton tapi belum bayar—eh, belum subscribe, pocong berikutnya datang."
    else:
        beats = [
            {"start":0,"end":1,"purpose":"HOOK","visual":hook.get("visual", idea["hook"]),"action":"Open on the impossible visual immediately; no intro.","dialogue":hook.get("hook", idea["hook"]),"sound":"Sharp impact followed by a brief silence."},
            {"start":1,"end":3,"purpose":"CONTEXT","visual":"Medium shot establishes the character and location clearly.","action":"The character tries to act as if everything is normal.","dialogue":"“This is completely under control.”","sound":"Quiet room tone."},
            {"start":3,"end":6,"purpose":"CONFLICT","visual":"Close-up on the problem and the character's reaction.","action":"The problem gets visibly worse; keep the action readable.","dialogue":"“Okay. Slightly less under control.”","sound":"Small comic creak or rattle."},
            {"start":6,"end":8,"purpose":"ESCALATION","visual":"Wider shot reveals an even more absurd consequence.","action":"A second problem appears and the character freezes.","dialogue":"“Nobody saw that, right?”","sound":"Rising tension sting."},
            {"start":8,"end":10,"purpose":"PAYOFF","visual":"Deadpan close-up; hold the reaction briefly after the final line.","action":"The character delivers the punchline without explaining it.","dialogue":"“I need a mechanic, not a doctor.”","sound":"Clean comedic sting, then cut."}
        ]
        punchline = "The character treats an impossible bodily problem like a routine repair job."
        cta = "Follow for the next disaster—this guy is still not fixed."
    return {
        "title": idea["title"],
        "logline": idea["premise"],
        "hook": {"visual": hook.get("visual", idea["hook"]), "dialogue": hook.get("hook", idea["hook"]), "duration_seconds": 1},
        "beats": beats,
        "punchline": punchline,
        "cta": cta,
        "return_potential": idea.get("series_potential", "A recurring character can return in a new everyday disaster."),
        "continuity_notes": [
            f"Keep the same {cfg['character']} appearance, proportions, and identifying details.",
            f"Maintain the same location and lighting across connected shots: {cfg['setting']}.",
            "The final frame should clearly establish the character pose and props for any continuation."
        ]
    }

def build_flow_prompts(cfg, story):
    beats = story.get("beats", [])
    chunks = []
    for i in range(0, len(beats), 5):
        segment = beats[i:i+5]
        start = segment[0].get("start", i*2)
        end = segment[-1].get("end", start+10)
        beat_text = []
        for b in segment:
            beat_text.append(
                f"{b.get('start')}–{b.get('end')}s | {b.get('purpose')}\n"
                f"Visual: {b.get('visual')}\nAction: {b.get('action')}\n"
                f"Dialogue: {b.get('dialogue')}\nSound: {b.get('sound')}"
            )
        prompt = f"""GOOGLE FLOW VIDEO PROMPT — SEGMENT {len(chunks)+1}
Duration: {min(10, end-start)} seconds maximum. Aspect ratio: 9:16 vertical.
Title: {story.get('title')}
Character: {cfg['character']}
Setting: {cfg['setting']}
Visual direction: realistic cinematic live-action / photorealistic CGI, detailed natural materials,
physically plausible lighting, sharp focus, believable motion, expressive but non-cartoon performance.
{realism_rules(cfg['mode'])}

TIMELINE:
{chr(10).join(beat_text)}

CONTINUITY:
{chr(10).join('- '+str(n) for n in story.get('continuity_notes', []))}
Keep the character design, proportions, clothing/accessories, location, props, and lighting consistent.
Use readable actions and one clear focal point at a time. Dialogue should be spoken naturally in
the language selected for this channel. Use subtle camera movement only when it improves clarity.
Do not add extra characters, dialogue, captions, logos, watermarks, or events not specified.
End on a stable frame that can connect to the next segment. Do not restart the story."""
        chunks.append({"segment": len(chunks)+1, "start": start, "end": end, "prompt": prompt})
    # Re-chunk long stories to max 10-second chunks if AI supplied many beats.
    return chunks

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
    api_key = st.text_input("Gemini API Key (opsional)", type="password", help="API key hanya digunakan dari sesi aplikasi ini. Jangan bagikan key.")
    model = st.text_input("Gemini model", value=DEFAULT_MODEL)
    st.caption("Tanpa API key, aplikasi tetap berjalan dengan contoh demo. Untuk ide cerita yang dinamis, isi API key Gemini.")
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

    # If user switches mode/theme, reset a previous preset that is no longer available.
    current_subtheme = st.session_state.get("subtheme", "")
    if current_subtheme not in subtheme_options and current_subtheme != "":
        st.session_state.subtheme_custom_value = current_subtheme
        st.session_state.subtheme_choice = custom_option
    elif st.session_state.get("subtheme_choice") not in subtheme_options:
        st.session_state.subtheme_choice = current_subtheme if current_subtheme in active_subthemes else active_subthemes[0]

    chosen_subtheme = st.selectbox(
        "Subtema", subtheme_options, key="subtheme_choice",
        help="Pilih subtema yang tersedia atau tulis ide sendiri."
    )
    if chosen_subtheme == custom_option:
        st.text_input(
            "Tulis subtema sendiri",
            key="subtheme_custom_value",
            placeholder="Contoh: pocong ketahuan nonton tapi tidak subscribe",
            help="Ide ini akan menjadi arahan utama generator cerita."
        )
        st.session_state.subtheme = st.session_state.get("subtheme_custom_value", "").strip()
    else:
        st.session_state.subtheme = chosen_subtheme

    if mode == "Indonesia Lokal":
        character_options = ["Pocong", "Kuntilanak", "Genderuwo", "Jin", "Manusia + Hantu Lokal"]
        setting_options = ["Kos-kosan Indonesia", "Warung pinggir jalan", "Kampung malam hari", "Rumah tua Indonesia", "Pos ronda", "Kantor Indonesia"]
        audience_options = ["Umum", "Remaja dan dewasa", "Ramah keluarga"]
        humor_options = ["Komedi absurd cepat", "Komedi deadpan", "Komedi horor", "Komedi keseharian"]
    elif mode == "Global Skeleton":
        character_options = ["Overconfident Skeleton", "Realistic Skeleton", "Ghost roommate", "Human + supernatural character"]
        setting_options = ["Small apartment", "Modern gym", "Office", "Supermarket", "Suburban street", "Hospital"]
        audience_options = ["General audience", "Teens and adults", "Family-friendly"]
        humor_options = ["Absurd, fast-paced, visual", "Deadpan comedy", "Horror-comedy", "Relatable everyday comedy"]
    else:
        character_options = ["Realistic Skeleton", "Overconfident Skeleton", "Pocong", "Kuntilanak", "Human + supernatural character"]
        setting_options = ["Apartment", "Kos-kosan Indonesia", "Warung", "Office", "Old house"]
        audience_options = ["General audience", "Remaja dan dewasa", "Family-friendly"]
        humor_options = ["Absurd comedy", "Komedi horor", "Deadpan comedy", "Relatable everyday comedy"]

    if st.session_state.get("character") not in character_options:
        st.session_state.character = character_options[0]
    if st.session_state.get("setting") not in setting_options:
        st.session_state.setting = setting_options[0]
    st.selectbox("Karakter utama", character_options, key="character")
    st.selectbox("Lokasi utama", setting_options, key="setting")
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
  <p>CLICK → STAY → RETURN · Studio perencanaan Shorts dengan hook, cerita, prompt Flow, B-roll, dan CTA.</p>
  <span class="pill">Realistic visual</span><span class="pill">Hook Lab</span>
  <span class="pill">Story Engine</span><span class="pill">Flow prompts ≤10s</span>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="stage"><h4>🧲 CLICK</h4><div class="muted">Hook visual yang langsung terbaca.</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="stage"><h4>⏳ STAY</h4><div class="muted">Konflik berkembang sampai payoff.</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="stage"><h4>🔁 RETURN</h4><div class="muted">Karakter dan serial yang ingin diikuti.</div></div>', unsafe_allow_html=True)

st.info("Alur kerja: Generate ide → pilih judul → pilih hook → generate cerita → buat prompt Flow → buat B-roll → export.")

# ----------------------------- STEP 1: IDEAS -----------------------------
st.header("1. 💡 Idea Generator")
st.write(f"**Mode:** {cfg['mode']} · **Tema:** {cfg['theme']} / {cfg['subtheme']} · **Tujuan:** {cfg['goal']}")
col_a, col_b = st.columns([1, 3])
with col_a:
    idea_count = st.selectbox("Jumlah ide", [3, 5, 7], index=1)
with col_b:
    st.caption("Setiap ide wajib punya hook, konflik, twist, dan potensi serial.")
if st.button("🚀 Generate Ide", type="primary", use_container_width=True):
    clear_from("ideas")
    with st.spinner("Menyusun ide yang berbeda..."):
        try:
            result = ai_or_demo(make_ideas_prompt(cfg, idea_count), api_key, model, lambda: demo_ideas(cfg, idea_count))
            ideas = result.get("ideas", []) if isinstance(result, dict) else result
            if not ideas:
                raise ValueError("AI tidak mengembalikan daftar ide.")
            st.session_state.ideas = ideas
            st.session_state.notice = "Ide berhasil dibuat."
        except Exception as e:
            st.error(str(e))
if st.session_state.ideas:
    options = [f"{i+1}. {x.get('title','Untitled')}" for i, x in enumerate(st.session_state.ideas)]
    current_idx = next((i for i,x in enumerate(st.session_state.ideas) if x.get("title") == st.session_state.selected_title), 0)
    selected_label = st.selectbox("Pilih judul yang ingin dikembangkan", options, index=current_idx, key="idea_choice")
    selected_idx = options.index(selected_label)
    selected_idea = st.session_state.ideas[selected_idx]
    if selected_idea.get("title") != st.session_state.selected_title:
        st.session_state.selected_title = selected_idea.get("title", "")
        st.session_state.selected_idea = selected_idea
        invalidate_downstream("hooks")
    st.markdown(f"### {selected_idea.get('title','')}")
    st.write(selected_idea.get("premise", ""))
    a, b = st.columns(2)
    with a:
        st.markdown("**Hook awal**")
        st.write(selected_idea.get("hook", ""))
        st.markdown("**Konflik**")
        st.write(selected_idea.get("conflict", ""))
    with b:
        st.markdown("**Twist / payoff**")
        st.write(selected_idea.get("twist", ""))
        st.markdown("**Potensi serial**")
        st.write(selected_idea.get("series_potential", ""))

# ----------------------------- STEP 2: HOOK LAB -----------------------------
st.divider()
st.header("2. 🧲 Hook Lab")
if not st.session_state.selected_idea:
    st.caption("Generate ide dan pilih judul terlebih dahulu.")
else:
    if st.button("Buat 3 Alternatif Hook", use_container_width=True):
        invalidate_downstream("hooks")
        with st.spinner("Menguji tiga pendekatan hook..."):
            try:
                result = ai_or_demo(
                    make_hooks_prompt(cfg, st.session_state.selected_idea),
                    api_key, model,
                    lambda: demo_hooks(cfg, st.session_state.selected_idea),
                )
                st.session_state.hooks = result.get("hooks", [])
                if not st.session_state.hooks:
                    raise ValueError("Hook tidak berhasil dibuat.")
            except Exception as e:
                st.error(str(e))
    if st.session_state.hooks:
        hook_labels = [f"{i+1}. {h.get('hook','Hook')}" for i,h in enumerate(st.session_state.hooks)]
        current_hook_idx = next((i for i,h in enumerate(st.session_state.hooks) if h.get("hook") == st.session_state.selected_hook), 0)
        hook_label = st.radio("Pilih hook utama", hook_labels, index=current_hook_idx, key="hook_choice")
        hook_idx = hook_labels.index(hook_label)
        selected_hook = st.session_state.hooks[hook_idx]
        if selected_hook.get("hook") != st.session_state.selected_hook:
            st.session_state.selected_hook = selected_hook.get("hook", "")
            invalidate_downstream("story")
        st.markdown(f"**Visual:** {selected_hook.get('visual','')}")
        st.markdown(f"**Rasa penasaran:** {selected_hook.get('curiosity','')}")
        st.markdown(f"**Kekuatan:** {selected_hook.get('strength','')}")

# ----------------------------- STEP 3: STORY -----------------------------
st.divider()
st.header("3. ⏳ Story Engine")
if not st.session_state.selected_idea or not st.session_state.selected_hook:
    st.caption("Pilih judul dan hook terlebih dahulu.")
else:
    st.caption("Cerita demo menggunakan struktur 10 detik. Dengan Gemini, cerita disesuaikan dengan judul dan hook pilihan.")
    if st.button("🎬 Generate Cerita Lengkap", type="primary", use_container_width=True):
        invalidate_downstream("story")
        hook_obj = next((h for h in st.session_state.hooks if h.get("hook") == st.session_state.selected_hook), {})
        with st.spinner("Membangun hook → konflik → eskalasi → punchline..."):
            try:
                story = ai_or_demo(
                    make_story_prompt(cfg, st.session_state.selected_idea, hook_obj),
                    api_key, model,
                    lambda: demo_story(cfg, st.session_state.selected_idea, hook_obj),
                    temperature=0.8,
                )
                # Ensure chosen title is the source of truth.
                story["title"] = st.session_state.selected_idea["title"]
                st.session_state.story = story
            except Exception as e:
                st.error(str(e))
    if st.session_state.story:
        story = st.session_state.story
        st.subheader(story.get("title", "Story"))
        st.write(story.get("logline", ""))
        beats = story.get("beats", [])
        if beats:
            st.dataframe(
                [{"Waktu": f"{b.get('start','?')}–{b.get('end','?')}s", "Fungsi": b.get("purpose",""), "Visual": b.get("visual",""), "Aksi": b.get("action",""), "Dialog": b.get("dialogue",""), "Suara": b.get("sound","")} for b in beats],
                use_container_width=True, hide_index=True
            )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Punchline**")
            st.write(story.get("punchline", ""))
        with c2:
            st.markdown("**CTA terintegrasi**")
            st.write(story.get("cta", "") or "Tidak perlu CTA verbal — biarkan punchline bekerja.")
        st.markdown("**Alasan penonton kembali**")
        st.write(story.get("return_potential", ""))
        with st.expander("Catatan kesinambungan"):
            for note in story.get("continuity_notes", []):
                st.write("• " + str(note))

# ----------------------------- STEP 4: FLOW -----------------------------
st.divider()
st.header("4. 🎥 Google Flow Prompt Engine")
if not st.session_state.story:
    st.caption("Generate cerita terlebih dahulu.")
else:
    if st.button("Buat Prompt Flow (maksimal 10 detik per segmen)", use_container_width=True):
        with st.spinner("Menyusun prompt video dan kesinambungan..."):
            try:
                story = st.session_state.story
                if api_key:
                    flow_request = f"""
Return JSON only: {{"segments":[{{"segment":1,"start":0,"end":10,"prompt":"..."}},...]}}
Create video prompts for this exact story. Split into segments no longer than 10 seconds, respecting total duration {cfg['duration']} seconds.
Story JSON: {json.dumps(story, ensure_ascii=False)}
Character: {cfg['character']}; location: {cfg['setting']}; visual style: {cfg['style']}.
{realism_rules(cfg['mode'])}
Each segment must continue from the previous segment without restarting. Preserve dialogue, props, character design, and timeline.
"""
                    result = gemini_generate(flow_request, api_key, model, 0.6)
                    segments = result.get("segments", [])
                    # Validate and clamp duration; do not silently accept >10-second segments.
                    clean = []
                    for i, seg in enumerate(segments):
                        start = int(seg.get("start", i*10))
                        end = int(seg.get("end", min(start+10, cfg["duration"])))
                        if end <= start:
                            end = start + 10
                        if end-start > 10:
                            end = start + 10
                        clean.append({"segment": i+1, "start": start, "end": end, "prompt": seg.get("prompt", "")})
                    st.session_state.flow_prompts = clean
                else:
                    st.session_state.flow_prompts = build_flow_prompts(cfg, story)
                if not st.session_state.flow_prompts:
                    raise ValueError("Prompt Flow kosong.")
            except Exception as e:
                st.error(str(e))
    if st.session_state.flow_prompts:
        for seg in st.session_state.flow_prompts:
            with st.expander(f"SEGMENT {seg['segment']} · {seg['start']}–{seg['end']} detik", expanded=(seg["segment"] == 1)):
                st.code(seg["prompt"], language="text")
                st.download_button(
                    f"⬇️ Download prompt segmen {seg['segment']}",
                    data=seg["prompt"],
                    file_name=f"flow_prompt_{seg['segment']:02d}.txt",
                    mime="text/plain",
                    key=f"download_flow_{seg['segment']}"
                )

# ----------------------------- STEP 5: BROLL -----------------------------
st.divider()
st.header("5. 🎞️ B-roll Engine")
if not st.session_state.story:
    st.caption("Generate cerita terlebih dahulu.")
else:
    if st.button("Buat 5 Prompt B-roll", use_container_width=True):
        try:
            if api_key:
                result = gemini_generate(make_broll_prompt(cfg, st.session_state.story), api_key, model, 0.7)
            else:
                result = demo_broll(cfg, st.session_state.story)
            st.session_state.broll = result.get("broll", [])
        except Exception as e:
            st.error(str(e))
    if st.session_state.broll:
        for i, shot in enumerate(st.session_state.broll):
            with st.expander(f"{i+1}. {shot.get('type','B-roll')} · {shot.get('duration_seconds',2)}s"):
                st.write(shot.get("purpose", ""))
                st.code(shot.get("prompt", ""), language="text")

# ----------------------------- STEP 6: EXPORT -----------------------------
st.divider()
st.header("6. 📦 Export")
if st.session_state.story:
    export_obj = {
        "app": APP_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config": cfg,
        "selected_idea": st.session_state.selected_idea,
        "selected_hook": next((h for h in st.session_state.hooks if h.get("hook") == st.session_state.selected_hook), {}),
        "story": st.session_state.story,
        "flow_prompts": st.session_state.flow_prompts,
        "broll": st.session_state.broll,
    }
    export_json = json.dumps(export_obj, ensure_ascii=False, indent=2)
    export_text = [
        f"CADAS RESONANCE STUDIO — {st.session_state.story.get('title','')}",
        "="*72,
        f"MODE: {cfg['mode']} | THEME: {cfg['theme']} / {cfg['subtheme']}",
        f"GOAL: {cfg['goal']} | TOTAL DURATION TARGET: {cfg['duration']} seconds",
        "",
        "STORY",
        json.dumps(st.session_state.story, ensure_ascii=False, indent=2),
        "",
        "GOOGLE FLOW PROMPTS",
    ]
    for seg in st.session_state.flow_prompts:
        export_text.append(f"\n--- SEGMENT {seg['segment']} ({seg['start']}–{seg['end']}s) ---\n{seg['prompt']}")
    export_text.append("\nB-ROLL")
    export_text.append(json.dumps(st.session_state.broll, ensure_ascii=False, indent=2))
    text_file = "\n".join(export_text)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Download semua sebagai TXT", text_file, file_name="cadas_resonance_output.txt", mime="text/plain", use_container_width=True)
    with c2:
        st.download_button("⬇️ Download project JSON", export_json, file_name="cadas_resonance_project.json", mime="application/json", use_container_width=True)
else:
    st.caption("Hasil export muncul setelah cerita dibuat.")

st.divider()
with st.expander("🛠️ Cara menjalankan"):
    st.code("pip install streamlit requests\nstreamlit run app.py", language="bash")
    st.write("1. Simpan file ini sebagai `app.py`.")
    st.write("2. Jalankan perintah di atas di terminal atau environment Streamlit.")
    st.write("3. Untuk ide dinamis, masukkan Gemini API Key di sidebar. Tanpa key, mode demo tetap bisa dicoba.")
    st.warning("Jangan pernah mengunggah atau membagikan API key. Biaya dan kuota API mengikuti akun penyedia API.")
