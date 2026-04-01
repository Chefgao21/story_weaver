import json
import re
import time
from datetime import datetime
from typing import Optional
import streamlit as st
from groq import Groq, RateLimitError, APIConnectionError, APIStatusError
import os
from dotenv import load_dotenv

load_dotenv()


# Groq client 

def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("❌ GROQ_API_KEY not found. Make sure your .env file exists and has the key.")
        st.stop()
    return Groq(api_key=api_key)


def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    retries: int = 3,
) -> Optional[str]:
    """
    Call the Groq API with retry logic and friendly error handling.
    Returns the response string or None on failure.
    """
    client = get_client()

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()

        except RateLimitError:
            wait = 10 * (attempt + 1)
            if attempt < retries - 1:
                st.warning(f"⏳ Rate limit reached. Retrying in {wait}s… (attempt {attempt+1}/{retries})")
                placeholder = st.empty()
                for remaining in range(wait, 0, -1):
                    placeholder.info(f"⏳ Waiting {remaining}s before retry…")
                    time.sleep(1)
                placeholder.empty()
            else:
                st.error("🚫 Rate limit reached and retries exhausted. Please wait a minute and try again.")
                return None

        except APIConnectionError:
            st.error("🔌 Connection error — check your internet connection.")
            return None

        except APIStatusError as e:
            st.error(f"⚠️ API error {e.status_code}: {e.message}")
            return None

        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None

    return None


# Story helpers 

def get_full_story_text(turns: list) -> str:
    """Concatenate all story turns into one narrative string."""
    return "\n\n".join(t["content"] for t in turns if t["content"].strip())


def parse_json_response(text: str) -> Optional[any]:
    """
    Safely parse JSON from LLM output.
    Strips markdown fences if present.
    """
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
    return None


# Story bible 

def maybe_update_story_bible(turns: list) -> dict:
    """
    Generates or refreshes the story bible based on AI turn count.

    Logic:
    - Does nothing for the first 7 AI turns (story too short to need it)
    - Generates the bible for the first time at turn 8
    - Refreshes every 5 AI turns after that (turns 13, 18, 23, ...)
    - If the API call fails, silently returns the last good bible
    - Never blocks the story — failure is always safe
    """
    from prompts import build_story_bible_prompt

    ai_turn_count = sum(1 for t in turns if t["role"] == "ai")

    # Not enough story yet — skip
    if ai_turn_count < 8:
        return st.session_state.get("story_bible", {})

    # Only regenerate at turn 8, then every 5 turns
    if ai_turn_count != 8 and ai_turn_count % 5 != 0:
        return st.session_state.get("story_bible", {})

    full_story = get_full_story_text(turns)
    result = call_llm(
        system_prompt="You are a precise story analyst. Return only valid JSON, no markdown, no explanation.",
        user_message=build_story_bible_prompt(full_story),
        temperature=0.2,
        max_tokens=400,
    )

    if result:
        parsed = parse_json_response(result)
        if isinstance(parsed, dict) and parsed:
            return parsed

    # Fall back to whatever we had before
    return st.session_state.get("story_bible", {})


# Export 

def export_markdown(
    title: str,
    genre: str,
    hook: str,
    turns: list,
    characters: dict,
) -> str:
    """Generate a clean Markdown export of the full story."""
    lines = []
    lines.append(f"# {title}")
    lines.append(f"\n*Genre: {genre}*\n")

    if characters:
        lines.append("## Characters\n")
        for name, desc in characters.items():
            lines.append(f"- **{name}**: {desc}")
        lines.append("")

    lines.append("## Story\n")
    for turn in turns:
        if turn["role"] == "user_addition" and turn["content"].strip():
            lines.append(f"> *{turn['content'].strip()}*\n")
        else:
            lines.append(turn["content"].strip())
            lines.append("")

    lines.append("---")
    lines.append(f"*Written with Story Weaver on {datetime.now().strftime('%B %d, %Y')}*")
    return "\n".join(lines)