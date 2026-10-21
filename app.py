import streamlit as st
import json
import os
import re
from openai import OpenAI

# ============================================================
# CADAS RESONANCE STUDIO
# ============================================================

st.set_page_config(
    page_title="Cadas Resonance Studio",
    page_icon="ðŸ’€",
    layout="wide"
)

API_BASE_URL = "https://clariohub.id/v1"

DEFAULT_TITLE_MODEL = "clario/gemini-3.7-flash"
DEFAULT_STORY_MODEL = "clario/deepseek-v4-pro"
DEFAULT_FLOW_MODEL = "clario/deepseek-v4-pro"

MODEL_OPTIONS = [
    "clario/gemini-3.7-flash",
    "clario/deepseek-v4-pro",
    "clario/deepseek-v4-flash",
    "clario/gpt-5.6-sol",
    "clario/glm-5.3-flash",
]

GLOBAL_THEMES = {
    "Skeleton Everyday Life": ["Morning Routine", "Going to Work", "Shopping", "Cooking", "Cleaning", "Sleeping"],
    "Absurd Comedy": ["Unexpected Disaster", "Ridiculous Argument", "Awkward Situation", "Unexpected Twist"],
    "Horror Comedy": ["Haunted House", "Ghost Encounter", "Creepy Neighbor", "Midnight Mystery"],
    "Gaming Comedy": ["Rage Quit", "Noob Moment", "Boss Fight", "Gaming Addiction"],
    "Relationship Comedy": ["Dating Problems", "Jealousy", "Breakup", "Awkward Date"],
    "Gym & Fitness": ["First Day at Gym", "Leg Day", "Protein Addiction", "Fitness Fail"],
    "Money & Work": ["Broke Again", "Salary Day", "Office Problems", "Unexpected Expenses"],
    "Food Comedy": ["Cooking Disaster", "Food Addiction", "Restaurant Problems", "Late Night Cravings"],
    "Science & Sci-Fi": ["Time Travel", "Alien Encounter", "Mad Experiment", "Robot Problems"],
    "Survival Comedy": ["Zombie Apocalypse", "Lost in the Woods", "Surviving the Night", "Disaster Survival"],
}

LOCAL_THEMES = {
    "Horor Komedi": ["Pocong Salah Alamat", "Kuntilanak Kesepian", "Genderuwo Numpang WiFi", "Tuyul Kena Tilang", "Hantu Kos", "Misteri Pos Ronda"],
    "Kehidupan Sehari-hari": ["Bangun Kesiangan", "Dompet Kosong", "Antre Makanan", "Motor Mogok", "Utang Teman"],
    "Komedi Tongkrongan": ["Teman Sok Kaya", "Debat Tidak Penting", "Mabar Sampai Pagi", "Teman Paling Pelit"],
    "Cerita Anak Kos": ["Akhir Bulan", "Mi Instan Terakhir", "Tagihan Listrik", "Iuran Kos", "Dikejar Pemilik Kos"],
}
CTA_OPTIONS = ["Smart Auto", "Comedy CTA", "Cliffhanger CTA", "Challenge CTA", "No CTA"]
DURATION_OPTIONS = [5, 8, 10, 15, 20, 30, 40, 50, 60]

DEFAULT_STATE = {
    "ideas": [], "selected_title": "", "story": None,
    "flow_prompts": [], "broll_prompts": [],
    "generated_title": "", "generated_story_title": "",
    "generated_flow_title": "", "generated_duration": None,
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def get_api_key():
    try:
        key = st.secrets.get("CLARIOHUB_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("CLARIOHUB_API_KEY", "")


def get_client():
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API key belum ditemukan. Tambahkan CLARIOHUB_API_KEY di Streamlit Secrets.")
    return OpenAI(api_key=api_key, base_url=API_BASE_URL)


def call_model(model, system_prompt, user_prompt, temperature=0.8):
    response = get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("AI mengembalikan respons kosong.")
    return content.strip()


def parse_json_response(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise ValueError(f"Respons AI bukan JSON valid: {exc}. Coba generate ulang.") from exc
    raise ValueError("Respons AI tidak mengandung objek JSON yang valid.")


def get_visual_style(mode):
    if mode == "ðŸŒŽ Global Skeleton":
        return """
PHOTOREALISTIC LIVE-ACTION-STYLE CGI, NOT CARTOON.
A believable full-size human skeleton with realistic bone texture,
natural proportions, physically based rendering, real-world materials,
cinematic but natural lighting, realistic shadows, detailed environments,
natural movement and believable camera optics. Keep skull shape, bone
proportions, and identifying details identical across every shot.
No cartoon, no Pixar, no toy-like plastic, no flat illustration.
"""
    return """
PHOTOREALISTIC LIVE-ACTION-STYLE SUPERNATURAL COMEDY, NOT CARTOON.
Realistic Indonesian environments, practical-looking materials, detailed
surfaces, cinematic natural lighting, realistic shadows, believable camera
optics and natural movement. Supernatural characters must look tangible
and retain exactly the same appearance across all shots.
No cartoon, no Pixar, no toy-like plastic, no flat illustration.
"""


def get_language(mode):
    return "Bahasa Indonesia yang natural dan kasual." if mode == "ðŸ‡®ðŸ‡© Indonesia Lokal" else "Natural conversational English."


def get_theme_context(mode, theme, subtheme):
    return f"MODE: {mode}\nTHEME: {theme}\nSUBTHEME: {subtheme}\nLANGUAGE: {get_language(mode)}\nKeep the story specific to the selected theme and subtheme."


def generate_ideas(mode, theme, subtheme, user_idea, title_model, number_of_ideas=5):
    system = """You are an expert short-form cinematic comedy writer. Return JSON only:
{"ideas":[{"title":"Title","concept":"Specific story concept","hook":"Opening hook","conflict":"Main conflict","punchline":"Ending twist"}]}
Create distinct, clickable, visually clear concepts. No markdown or extra commentary."""
    user = f"""{get_theme_context(mode, theme, subtheme)}
USER IDEA: {user_idea or "Invent an original idea based on the selected theme."}
Create exactly {number_of_ideas} distinct concepts. Each title must lead to a genuinely different story."""
    data = parse_json_response(call_model(title_model, system, user, 0.95))
    ideas = data.get("ideas", [])
    if not ideas:
        raise ValueError("AI tidak menghasilkan pilihan judul.")
    return ideas


def generate_story(mode, theme, subtheme, selected_title, selected_concept, duration, cta_style, story_model):
    system = """You are a professional short-form screenplay writer. The selected title is authoritative:
write a story specifically for it, never substitute another title or reuse an unrelated plot.
Include a visual hook in the first second, clear conflict, natural concise dialogue,
escalation, memorable punchline, and context-specific CTA when requested. Respect duration.
Return JSON only:
{"title":"Selected title","logline":"Premise","characters":[{"name":"Name","visual_description":"Detailed consistent appearance","personality":"Personality","voice":"Voice"}],"setting":"Setting","hook":"Hook","conflict":"Conflict","story_beats":[{"time":"0-3s","action":"Action","dialogue":"Dialogue","emotion":"Emotion"}],"punchline":"Twist","cta":"CTA or empty string","ending_frame":"Final visual state","continuity_notes":"Continuity details"}"""
    user = f"""{get_theme_context(mode, theme, subtheme)}
SELECTED TITLE: {selected_title}
SELECTED CONCEPT: {selected_concept}
TOTAL DURATION: {duration} seconds
CTA STYLE: {cta_style}
VISUAL STYLE: {get_visual_style(mode)}
Make the hook instantly visual, dialogue short enough to fit, and ending memorable.
For videos longer than 10 seconds, distribute events across connected segments.
Keep character, props, and setting consistent. Use {get_language(mode)}."""
    story = parse_json_response(call_model(story_model, system, user, 0.85))
    story["title"] = selected_title
    return story


def split_duration(total_duration):
    segments, remaining = [], int(total_duration)
    while remaining > 0:
        part = min(10, remaining)
        segments.append(part)
        remaining -= part
    return segments


def extract_ending_frame(prompt):
    marker = "ENDING FRAME FOR CONTINUITY:"
    if marker in prompt:
        return prompt.split(marker, 1)[1].strip()
    return "Continue from the exact preceding final frame; preserve character and prop positions, lighting, environment, and camera continuity."


def generate_flow_segment(mode, theme, subtheme, story, segment_index, segment_count,
                          segment_duration, total_duration, previous_ending, flow_model):
    first, last = segment_index == 1, segment_index == segment_count
    if first and last:
        role = "ONLY SEGMENT: tell the complete story from hook through conflict and punchline; finish with CTA if appropriate."
    elif first:
        role = """FIRST SEGMENT: open with the strongest visual hook, introduce and escalate the conflict,
do not resolve everything. End on a precise frame for the next segment: character poses,
positions, props, background, lighting, and camera framing."""
    elif last:
        role = """FINAL SEGMENT: continue directly from the previous final frame; no recap or repeated hook.
Resolve the conflict and deliver the strongest punchline. Add a natural CTA only if it fits."""
    else:
        role = """MIDDLE SEGMENT: continue directly from the previous final frame; no recap or repeated hook.
Escalate the conflict, do not reveal the final punchline, and end with a precise handoff frame."""
    system = """You are an expert Google Flow prompt engineer. Return ONE ready-to-paste plain-text prompt,
not JSON and without markdown fences. Prompt exactly the requested duration, maximum 10 seconds.
Specify character appearance, setting, timed action/dialogue, camera movement, lighting, sound,
realistic motion, continuity, and ending frame. Dialogue must fit the time."""
    user = f"""Create segment {segment_index}/{segment_count}.
SEGMENT DURATION: exactly {segment_duration} seconds. TOTAL VIDEO: {total_duration} seconds.
FORMAT: vertical 9:16.
{get_theme_context(mode, theme, subtheme)}
TITLE: {story.get('title','')}
PREMISE: {story.get('logline','')}
CHARACTERS: {json.dumps(story.get('characters', []), ensure_ascii=False)}
SETTING: {story.get('setting','')}
HOOK: {story.get('hook','')}
CONFLICT: {story.get('conflict','')}
STORY BEATS: {json.dumps(story.get('story_beats', []), ensure_ascii=False)}
PUNCHLINE: {story.get('punchline','')}
CTA: {story.get('cta','')}
VISUAL STYLE: {get_visual_style(mode)}
SEGMENT ROLE: {role}
PREVIOUS SEGMENT ENDING: {previous_ending or 'No previous segment; start from the opening hook.'}
Continuity: same character design, outfit, props, location, time of day, lighting direction, and palette.
The first frame must logically match the prior segment's last frame. No unexplained new characters/objects.
No subtitles, captions, watermarks, or text overlays.
Provide a timeline from 0.0 to {segment_duration}.0 seconds that totals exactly {segment_duration} seconds.
Include ambience and synchronized sound effects. End with:
ENDING FRAME FOR CONTINUITY: [describe exact final visual state]."""
    return call_model(flow_model, system, user, 0.65)


def generate_all_flow_prompts(mode, theme, subtheme, story, total_duration, flow_model, progress_callback=None):
    durations = split_duration(total_duration)
    prompts, previous_ending = [], ""
    for index, segment_duration in enumerate(durations, start=1):
        if progress_callback:
            progress_callback(index, len(durations), segment_duration)
        prompt = generate_flow_segment(
            mode, theme, subtheme, story, index, len(durations),
            segment_duration, total_duration, previous_ending, flow_model
        )
        prompts.append({
            "segment": index,
            "duration": segment_duration,
            "title": story.get("title", ""),
            "prompt": prompt,
        })
        previous_ending = extract_ending_frame(prompt)
    return prompts


def generate_broll(mode, story, flow_model):
    system = """You are a cinematic video director. Return JSON only:
{"broll":[{"title":"Shot name","prompt":"Complete prompt"}]}
Create exactly five distinct supporting shots: establishing, character reaction/detail,
important prop close-up, escalation/suspense, and punchline reaction. Specify action,
lighting, camera, environment, continuity, photorealistic CGI. No markdown."""
    user = f"""TITLE: {story.get('title','')}
STORY: {json.dumps(story, ensure_ascii=False)}
STYLE: {get_visual_style(mode)}
For skeleton stories, each prompt should begin "Place the skeleton character...".
For Indonesian supernatural stories, use the actual character rather than forcing a skeleton.
Avoid repeated compositions and preserve continuity."""
    return parse_json_response(call_model(flow_model, system, user, 0.75)).get("broll", [])


# ----------------------------- SIDEBAR -----------------------------
st.sidebar.title("ðŸ’€ Cadas Resonance Studio")
st.sidebar.caption("Cinematic AI Story & Google Flow Prompt Studio")
mode = st.sidebar.selectbox("ðŸŒ Mode", ["ðŸŒŽ Global Skeleton", "ðŸ‡®ðŸ‡© Indonesia Lokal"])
title_model = st.sidebar.selectbox("ðŸ§  Model Judul / Ide", MODEL_OPTIONS, index=0)
story_model = st.sidebar.selectbox("âœï¸ Model Cerita", MODEL_OPTIONS, index=1)
flow_model = st.sidebar.selectbox("ðŸŽ¬ Model Google Flow", MODEL_OPTIONS, index=1)

theme_options = list(LOCAL_THEMES) if mode == "ðŸ‡®ðŸ‡© Indonesia Lokal" else list(GLOBAL_THEMES)
theme = st.sidebar.selectbox("ðŸŽ­ Tema", theme_options)
subtheme_options = LOCAL_THEMES[theme] if mode == "ðŸ‡®ðŸ‡© Indonesia Lokal" else GLOBAL_THEMES[theme]
subtheme = st.sidebar.selectbox("ðŸŽ¯ Subtema", subtheme_options)
duration = st.sidebar.selectbox("â±ï¸ Durasi Total Video", DURATION_OPTIONS, index=DURATION_OPTIONS.index(20))
cta_style = st.sidebar.selectbox("ðŸ“¢ Gaya CTA", CTA_OPTIONS)
st.sidebar.caption(f"{duration} detik = {len(split_duration(duration))} prompt; maksimal 10 detik per prompt.")

# ----------------------------- MAIN UI -----------------------------
st.title("ðŸ’€ Cadas Resonance Studio")
st.markdown("Generate cerita, hook, punchline, CTA, dan prompt Google Flow dengan kesinambungan antarsemen.")
user_idea = st.text_area("ðŸ’¡ Ide awal cerita", placeholder="Contoh: skeleton pergi ke gym tetapi takut melihat tulangnya sendiri." if mode == "ðŸŒŽ Global Skeleton" else "Contoh: pocong menagih utang ke anak kos pada akhir bulan.", height=100)

col1, col2 = st.columns(2)
with col1:
    generate_ideas_button = st.button("ðŸŽ² Generate Ideas", type="primary", use_container_width=True)
with col2:
    generate_story_button = st.button("âœï¸ Generate Story", use_container_width=True)

if generate_ideas_button:
    try:
        with st.spinner("Membuat pilihan ide dan judul..."):
            ideas = generate_ideas(mode, theme, subtheme, user_idea, title_model)
        st.session_state.ideas = ideas
        st.session_state.selected_title = ""
        st.session_state.story = None
        st.session_state.flow_prompts = []
        st.session_state.broll_prompts = []
        st.session_state.generated_title = ""
        st.session_state.generated_story_title = ""
        st.session_state.generated_flow_title = ""
        st.session_state.generated_duration = None
        st.success("Ide baru berhasil dibuat.")
    except Exception as exc:
        st.error(f"Gagal membuat ide: {exc}")

if st.session_state.ideas:
    st.subheader("ðŸ“ Pilih Judul Cerita")
    title_options = [idea.get("title", f"Ide {i+1}") for i, idea in enumerate(st.session_state.ideas)]
    current = st.session_state.selected_title
    default_index = title_options.index(current) if current in title_options else 0
    selected_title = st.selectbox("Judul yang akan digunakan", title_options, index=default_index, key="title_selector")
    selected_idea = next((idea for idea in st.session_state.ideas if idea.get("title") == selected_title), None)
    if selected_idea:
        st.markdown(f"**Konsep:** {selected_idea.get('concept','')}")
        st.markdown(f"**Hook:** {selected_idea.get('hook','')}")
        st.markdown(f"**Konflik:** {selected_idea.get('conflict','')}")
        st.markdown(f"**Punchline:** {selected_idea.get('punchline','')}")
    if selected_title != st.session_state.selected_title:
        st.session_state.selected_title = selected_title
        st.session_state.story = None
        st.session_state.flow_prompts = []
        st.session_state.broll_prompts = []
        st.session_state.generated_story_title = ""
        st.session_state.generated_flow_title = ""
        st.session_state.generated_duration = None

if generate_story_button:
    if not st.session_state.ideas:
        st.warning("Generate Ideas terlebih dahulu.")
    elif not st.session_state.selected_title:
        st.warning("Pilih judul terlebih dahulu.")
    else:
        selected_idea = next((idea for idea in st.session_state.ideas if idea.get("title") == st.session_state.selected_title), None)
        if not selected_idea:
            st.error("Konsep judul tidak ditemukan. Generate Ideas ulang.")
        else:
            try:
                with st.spinner("Menulis cerita berdasarkan judul pilihan..."):
                    story = generate_story(mode, theme, subtheme, st.session_state.selected_title,
                                           selected_idea.get("concept", ""), duration, cta_style, story_model)
                st.session_state.story = story
                st.session_state.generated_title = st.session_state.selected_title
                st.session_state.generated_story_title = st.session_state.selected_title
                st.session_state.flow_prompts = []
                st.session_state.broll_prompts = []
                st.session_state.generated_flow_title = ""
                st.session_state.generated_duration = None
                st.success("Cerita berhasil dibuat.")
            except Exception as exc:
                st.error(f"Gagal membuat cerita: {exc}")

story = st.session_state.story
if story:
    if story.get("title") != st.session_state.selected_title or st.session_state.generated_story_title != st.session_state.selected_title:
        st.warning("Judul berubah. Klik Generate Story kembali sebelum membuat prompt agar cerita tidak tertukar.")
    else:
        st.divider()
        st.header("ðŸ“– Cerita")
        st.subheader(story.get("title", ""))
        st.write(story.get("logline", ""))
        with st.expander("ðŸ‘¥ Karakter", expanded=True):
            for character in story.get("characters", []):
                st.markdown(f"### {character.get('name', 'Karakter')}")
                st.write(f"**Visual:** {character.get('visual_description', '')}")
                st.write(f"**Kepribadian:** {character.get('personality', '')}")
                st.write(f"**Suara:** {character.get('voice', '')}")
        st.markdown(f"**Lokasi:** {story.get('setting', '')}")
        st.markdown(f"**Hook:** {story.get('hook', '')}")
        st.markdown(f"**Konflik:** {story.get('conflict', '')}")
        st.subheader("ðŸŽ­ Alur Cerita")
        for i, beat in enumerate(story.get("story_beats", []), 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {beat.get('time', '')}**")
                st.write(beat.get("action", ""))
                st.write(f"ðŸ—£ï¸ {beat.get('dialogue', '')}")
                st.caption(f"Emosi: {beat.get('emotion', '')}")
        st.markdown(f"**Punchline:** {story.get('punchline', '')}")
        st.markdown(f"**CTA:** {story.get('cta', '')}")

if story:
    st.divider()
    st.header("ðŸŽ¬ Google Flow Prompts")
    current_story_matches = story.get("title") == st.session_state.selected_title and st.session_state.generated_story_title == st.session_state.s
