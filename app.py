import streamlit as st
from prompts import (
    GENRE_RULES,
    GENRE_EMOJI,
    build_system_prompt,
    build_opening_prompt,
    build_continue_prompt,
    build_choices_prompt,
    build_choice_continue_prompt,
    build_character_extract_prompt,
    build_remix_prompt,
    build_viz_prompt,
)
from utils import (
    call_llm,
    get_full_story_text,
    parse_json_response,
    export_markdown,
    maybe_update_story_bible,
)

# ── Page config 
st.set_page_config(
    page_title="Story Weaver",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap');

    html, body, [class*="css"] { font-family: 'Lato', sans-serif; }

    .story-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.8rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .story-subtitle {
        text-align: center;
        color: #6b6b8a;
        font-size: 1rem;
        margin-bottom: 2rem;
        font-style: italic;
    }
    .story-box {
        background: #fdfaf5;
        border: 1px solid #e8e0d0;
        border-radius: 12px;
        padding: 2rem 2.5rem;
        font-family: 'Playfair Display', serif;
        font-size: 1.05rem;
        line-height: 1.9;
        color: #2c2c3e;
        max-height: 480px;
        overflow-y: auto;
        box-shadow: inset 0 1px 4px rgba(0,0,0,0.05);
    }
    .story-box p { margin-bottom: 1.2rem; }
    .user-addition {
        color: #7a5c38;
        font-style: italic;
        border-left: 3px solid #c9a96e;
        padding-left: 1rem;
        margin: 0.8rem 0;
    }
    .genre-badge {
        display: inline-block;
        background: #1a1a2e;
        color: #f0e6d3;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    .bible-badge {
        display: inline-block;
        background: #2d6a4f;
        color: #d8f3dc;
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-left: 8px;
        vertical-align: middle;
    }
    .char-card {
        background: #f5f0e8;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.5rem;
        border-left: 3px solid #c9a96e;
    }
    .char-name { font-weight: 700; color: #1a1a2e; font-size: 0.85rem; }
    .char-desc { color: #5a5a72; font-size: 0.8rem; }
    .section-header {
        font-family: 'Playfair Display', serif;
        font-size: 1rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.4rem;
        border-bottom: 1px solid #e8e0d0;
        padding-bottom: 0.3rem;
    }
    .info-box {
        background: #eef2ff;
        border-radius: 8px;
        padding: 0.7rem 1rem;
        font-size: 0.85rem;
        color: #3d3d6b;
        margin-bottom: 1rem;
    }
    .bible-box {
        background: #f0faf4;
        border: 1px solid #b7dfc5;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        font-size: 0.78rem;
        color: #2d6a4f;
        margin-top: 0.5rem;
    }
    [data-testid="stSidebar"] {
        background: #f9f5ee;
        border-right: 1px solid #e8e0d0;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# Session state defaults 
DEFAULTS = {
    "screen": "setup",
    "title": "",
    "genre": "Fantasy",
    "hook": "",
    "turns": [],
    "characters": {},
    "temperature": 0.75,
    "pending_choices": None,
    "remix_result": None,
    "story_bible": {},        # populated after 8 AI turns, refreshed every 5
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# Helpers 

def add_turn(role: str, content: str):
    st.session_state.turns.append({"role": role, "content": content})


def undo_last_ai_turn():
    turns = st.session_state.turns
    if not turns:
        return
    if turns and turns[-1]["role"] == "ai":
        turns.pop()
    if turns and turns[-1]["role"] == "user_addition":
        turns.pop()
    st.session_state.pending_choices = None


def get_system_prompt() -> str:
    """Build the system prompt, injecting the bible if it exists."""
    return build_system_prompt(
        st.session_state.genre,
        st.session_state.characters,
        st.session_state.get("story_bible", {}),
    )


def after_ai_turn():
    """
    Run after every AI turn:
    1. Extract / update characters
    2. Maybe update the story bible (only kicks in after turn 8)
    """
    full_story = get_full_story_text(st.session_state.turns)
    if not full_story.strip():
        return

    # Character extraction
    result = call_llm(
        system_prompt="You are a precise literary analyst. Return only valid JSON, no markdown, no explanation.",
        user_message=build_character_extract_prompt(full_story),
        temperature=0.2,
        max_tokens=512,
    )
    if result:
        parsed = parse_json_response(result)
        if isinstance(parsed, dict):
            for name, desc in parsed.items():
                if name not in st.session_state.characters:
                    st.session_state.characters[name] = desc

    # Story bible update (silent — won't block story if it fails)
    st.session_state.story_bible = maybe_update_story_bible(st.session_state.turns)


def render_story_html():
    if not st.session_state.turns:
        return "<p style='color:#aaa;font-style:italic;'>Your story will appear here…</p>"
    parts = []
    for turn in st.session_state.turns:
        content = turn["content"].strip()
        if not content:
            continue
        if turn["role"] == "user_addition":
            parts.append(f'<div class="user-addition">{content}</div>')
        else:
            paras = [p.strip() for p in content.split("\n") if p.strip()]
            for p in paras:
                parts.append(f"<p>{p}</p>")
    return "\n".join(parts)


def ai_turn_count() -> int:
    return sum(1 for t in st.session_state.turns if t["role"] == "ai")


# Screen: Setup 

def render_setup():
    st.markdown('<div class="story-title">📖 Story Weaver</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="story-subtitle">Your AI-powered collaborative storytelling companion</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 3, 1])
    with center:
        col1, col2 = st.columns([3, 1])
        with col1:
            title = st.text_input(
                "Story Title",
                placeholder="e.g. The Last Signal, Crimson Veil…",
                value=st.session_state.title,
                key="title_input",
            )
        with col2:
            genre_options = list(GENRE_RULES.keys())
            genre = st.selectbox(
                "Genre",
                genre_options,
                index=genre_options.index(st.session_state.genre),
            )

        hook = st.text_area(
            "Initial Hook / Setting",
            placeholder=(
                "Describe the opening scene or situation.\n\n"
                "e.g. A lone lighthouse keeper discovers a message in a bottle — "
                "written in their own handwriting, dated ten years in the future."
            ),
            value=st.session_state.hook,
            height=150,
            key="hook_input",
        )

        emoji = GENRE_EMOJI.get(genre, "📖")
        st.markdown(
            f'<div class="info-box">{emoji} <strong>{genre} mode:</strong> {GENRE_RULES[genre][:130]}…</div>',
            unsafe_allow_html=True,
        )

        start_disabled = not (
            st.session_state.get("title_input", "").strip()
            and st.session_state.get("hook_input", "").strip()
        )

        if st.button(
            "✨ Start the Story",
            type="primary",
            disabled=start_disabled,
            use_container_width=True,
        ):
            st.session_state.title = title.strip()
            st.session_state.genre = genre
            st.session_state.hook = hook.strip()
            st.session_state.turns = []
            st.session_state.characters = {}
            st.session_state.pending_choices = None
            st.session_state.remix_result = None
            st.session_state.story_bible = {}

            with st.spinner("✍️ Writing your opening…"):
                system = build_system_prompt(genre, {}, {})
                user_msg = build_opening_prompt(title, genre, hook)
                opening = call_llm(
                    system, user_msg,
                    temperature=st.session_state.temperature,
                    max_tokens=600,
                )

            if opening:
                add_turn("ai", opening)
                st.session_state.screen = "story"
                after_ai_turn()
                st.rerun()

        if start_disabled:
            st.caption("Fill in both the title and hook to begin.")


# Screen: Story 

def render_story():

    # Sidebar 
    with st.sidebar:
        st.markdown(
            f"### {GENRE_EMOJI.get(st.session_state.genre, '📖')} {st.session_state.title}"
        )
        st.markdown(
            f'<div class="genre-badge">{st.session_state.genre}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-header">🎨 Creativity</div>', unsafe_allow_html=True)
        st.session_state.temperature = st.slider(
            "Temperature",
            min_value=0.1,
            max_value=1.5,
            value=st.session_state.temperature,
            step=0.05,
            label_visibility="collapsed",
            help="Lower = more focused. Higher = more surprising.",
        )
        temp = st.session_state.temperature
        if temp < 0.5:
            st.caption("🧊 Focused & consistent")
        elif temp < 0.9:
            st.caption("✍️ Balanced creativity")
        elif temp < 1.2:
            st.caption("🔥 Wild & unpredictable")
        else:
            st.caption("🌀 Pure chaos — good luck")

        st.divider()

        st.markdown('<div class="section-header">📜 Genre Rules</div>', unsafe_allow_html=True)
        st.caption(GENRE_RULES.get(st.session_state.genre, ""))

        st.divider()

        # Characters
        st.markdown('<div class="section-header">👥 Characters</div>', unsafe_allow_html=True)
        if st.session_state.characters:
            for name, desc in st.session_state.characters.items():
                st.markdown(
                    f'<div class="char-card">'
                    f'<div class="char-name">{name}</div>'
                    f'<div class="char-desc">{desc}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Characters appear here as the story develops.")

        st.divider()

        # Story bible status
        bible = st.session_state.get("story_bible", {})
        turns_until_bible = max(0, 8 - ai_turn_count())

        if bible and any(bible.values()):
            st.markdown(
                '<div class="section-header">📚 Story Bible <span class="bible-badge">Active</span></div>',
                unsafe_allow_html=True,
            )
            with st.expander("View bible"):
                st.markdown(
                    f'<div class="bible-box">'
                    f'<strong>World:</strong> {bible.get("world_rules", "—")}<br><br>'
                    f'<strong>Key Events:</strong> {bible.get("key_events", "—")}<br><br>'
                    f'<strong>Characters:</strong> {bible.get("character_facts", "—")}<br><br>'
                    f'<strong>Open Threads:</strong> {bible.get("unresolved_threads", "—")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        elif turns_until_bible > 0:
            st.markdown('<div class="section-header">📚 Story Bible</div>', unsafe_allow_html=True)
            st.caption(f"Activates in {turns_until_bible} more AI turn{'s' if turns_until_bible != 1 else ''}.")

        st.divider()

        # Controls
        st.markdown('<div class="section-header">⚙️ Controls</div>', unsafe_allow_html=True)
        cola, colb = st.columns(2)
        with cola:
            if st.button("↩️ Undo", use_container_width=True, help="Remove the last AI turn"):
                undo_last_ai_turn()
                st.rerun()
        with colb:
            if st.button("🔄 New Story", use_container_width=True):
                st.session_state.screen = "setup"
                st.rerun()

        if st.session_state.turns:
            md = export_markdown(
                st.session_state.title,
                st.session_state.genre,
                st.session_state.hook,
                st.session_state.turns,
                st.session_state.characters,
            )
            st.download_button(
                "📥 Export as Markdown",
                data=md,
                file_name=f"{st.session_state.title.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

        full = get_full_story_text(st.session_state.turns)
        wc = len(full.split()) if full else 0
        st.caption(f"📝 {wc} words · {ai_turn_count()} AI turns")

    # Main area 
    st.markdown(
        f'<div class="story-title" style="font-size:2rem;">{st.session_state.title}</div>',
        unsafe_allow_html=True,
    )

    story_html = render_story_html()
    st.markdown(f'<div class="story-box">{story_html}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Choices flow 
    if st.session_state.pending_choices:
        choices = st.session_state.pending_choices
        st.markdown("### 🔀 Choose your direction")
        labels = [f"**{c['title']}** — {c['preview']}" for c in choices]
        chosen_idx = st.radio(
            "Where does the story go?",
            options=range(len(choices)),
            format_func=lambda i: labels[i],
            label_visibility="collapsed",
        )
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("✅ Go this way", type="primary"):
                chosen = choices[chosen_idx]
                full_story = get_full_story_text(st.session_state.turns)
                with st.spinner("✍️ Writing this path…"):
                    system = get_system_prompt()
                    user_msg = build_choice_continue_prompt(
                        full_story, chosen["title"], chosen["preview"]
                    )
                    result = call_llm(system, user_msg, temperature=st.session_state.temperature)
                if result:
                    add_turn("ai", result)
                    st.session_state.pending_choices = None
                    after_ai_turn()
                    st.rerun()
        with c2:
            if st.button("❌ Cancel"):
                st.session_state.pending_choices = None
                st.rerun()
        st.stop()

    # Remix result 
    if st.session_state.remix_result:
        remix = st.session_state.remix_result
        st.markdown(f"### 🎭 Remix: Latest passage as **{remix['new_genre']}**")
        remix_html = "".join(
            f"<p>{p.strip()}</p>"
            for p in remix["content"].split("\n") if p.strip()
        )
        st.markdown(
            f'<div class="story-box" style="max-height:220px;">{remix_html}</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("✅ Replace with remix", type="primary"):
                for i in range(len(st.session_state.turns) - 1, -1, -1):
                    if st.session_state.turns[i]["role"] == "ai":
                        st.session_state.turns[i]["content"] = remix["content"]
                        break
                st.session_state.genre = remix["new_genre"]
                st.session_state.remix_result = None
                st.rerun()
        with c2:
            if st.button("❌ Discard"):
                st.session_state.remix_result = None
                st.rerun()
        st.stop()

    # Input + action buttons 
    user_input = st.text_area(
        "Add your own sentences (optional — press a button below to continue)",
        placeholder="Type your contribution here, or leave blank to let the AI drive…",
        height=90,
        key="user_input_box",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✍️ Continue with AI", type="primary", use_container_width=True):
            if user_input.strip():
                add_turn("user_addition", user_input.strip())
            full_story = get_full_story_text(st.session_state.turns)
            with st.spinner("✍️ Continuing your story…"):
                system = get_system_prompt()
                user_msg = build_continue_prompt(full_story, "")
                result = call_llm(system, user_msg, temperature=st.session_state.temperature)
            if result:
                add_turn("ai", result)
                after_ai_turn()
                st.rerun()

    with col2:
        if st.button("🔀 Give Me Choices", use_container_width=True):
            if user_input.strip():
                add_turn("user_addition", user_input.strip())
            full_story = get_full_story_text(st.session_state.turns)
            with st.spinner("🧠 Generating story branches…"):
                system = get_system_prompt()
                user_msg = build_choices_prompt(full_story)
                result = call_llm(system, user_msg, temperature=0.9, max_tokens=512)
            if result:
                parsed = parse_json_response(result)
                if parsed and isinstance(parsed, list) and len(parsed) >= 2:
                    st.session_state.pending_choices = parsed
                    st.rerun()
                else:
                    st.error("Couldn't parse story choices — try again!")

    # Genre Remix 
    st.markdown("---")
    remix_col1, remix_col2 = st.columns([2, 1])
    with remix_col1:
        st.markdown("**🎭 Genre Remix** — rewrite the latest AI passage in a different genre:")
    with remix_col2:
        other_genres = [g for g in GENRE_RULES.keys() if g != st.session_state.genre]
        remix_target = st.selectbox("Target genre", other_genres, label_visibility="collapsed")

    col_a, col_b = st.columns([1, 2])
    with col_a:
        if st.button(f"Remix as {remix_target} →", use_container_width=True):
            last_ai = next(
                (t["content"] for t in reversed(st.session_state.turns) if t["role"] == "ai"),
                None,
            )
            if last_ai:
                with st.spinner(f"🎭 Rewriting as {remix_target}…"):
                    system = (
                        "You are a skilled author. Rewrite the given passage in a new genre "
                        "while preserving the same plot events and characters. "
                        "Write only the rewritten passage, nothing else."
                    )
                    user_msg = build_remix_prompt(last_ai, st.session_state.genre, remix_target)
                    result = call_llm(system, user_msg, temperature=0.8)
                if result:
                    st.session_state.remix_result = {"content": result, "new_genre": remix_target}
                    st.rerun()
            else:
                st.warning("No AI passage to remix yet.")

    # Visualization prompt 
    with col_b:
        if st.button("🎨 Generate Image Prompt", use_container_width=True):
            last_ai = next(
                (t["content"] for t in reversed(st.session_state.turns) if t["role"] == "ai"),
                None,
            )
            if last_ai:
                with st.spinner("🎨 Generating image prompt…"):
                    result = call_llm(
                        system_prompt="You are a visual artist who writes image generation prompts. Return only the prompt, nothing else.",
                        user_message=build_viz_prompt(last_ai),
                        temperature=0.7,
                        max_tokens=150,
                    )
                if result:
                    st.text_area(
                        "Copy this into DALL·E, Midjourney, or Flux",
                        value=result,
                        height=120,
                    )
            else:
                st.warning("No AI passage to visualize yet.")


# Router 

def main():
    if st.session_state.screen == "setup":
        render_setup()
    elif st.session_state.screen == "story":
        render_story()


if __name__ == "__main__":
    main()
