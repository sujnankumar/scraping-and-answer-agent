import os
import re
import html
import time
from typing import Dict, List
from urllib.parse import urlparse

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

# Reuse the existing research workflow from main.py
from main import run_research_system, llm

# Consistent preview size for snippets inside dropdowns
SNIPPET_MAX_CHARS = 450


def strip_markdown(text: str) -> str:
    """Remove common Markdown syntax to show plain text snippets."""
    # Images: ![alt](url) -> alt
    text = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", text)
    # Links: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    # Headings: ## Title -> Title
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Blockquotes: > quote -> quote
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    # Lists: -, *, +, 1. -> plain
    text = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", text, flags=re.MULTILINE)
    # Code spans: `code` -> code
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # Bold/italics: **text**, *text*, __text__, _text_ -> text
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    # Horizontal rules -> remove
    text = re.sub(r"^(?:-{3,}|_{3,}|\*{3,})\s*$", "", text, flags=re.MULTILINE)
    return text


st.set_page_config(
    page_title="Scrape & Answer - Research Agent",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Scrape & Answer – Research Agent")
st.caption("Enter a query to search the web and draft a concise answer with sources.")

# Minimal CSS to make all dropdown snippets the same visible size
st.markdown(
        """
        <style>
            /* Keep the query input and button on one row inside the form */
            div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap !important;
                align-items: center;
                gap: .5rem;
            }
            /* Make the submit button visually aligned */
            div[data-testid="stForm"] button {
                height: 40px;
            }

            .snippet-fixed { 
                line-height: 1.35; 
                max-height: calc(1.35em * 6); /* exactly ~6 lines */
                overflow: hidden; 
                display: -webkit-box; 
                -webkit-line-clamp: 6; 
                -webkit-box-orient: vertical; 
            }
        </style>
        """,
        unsafe_allow_html=True,
)


with st.form("query_form"):
    col1, col2 = st.columns([9, 0.9])
    query = col1.text_input(
        label="Your query",
        placeholder="e.g., In which year did IIT Bombay have a fest on March 20?",
        label_visibility="collapsed",
    )
    run = col2.form_submit_button("🔍", use_container_width=True)

if run:
    if not query.strip():
        st.warning("Please enter a query.")
        st.stop()

    start_ts = time.time()
    with st.spinner("Running research agents…"):
        result = run_research_system(query.strip())
    duration = time.time() - start_ts

    # Research process (compact)
    research_data: List[Dict] = result.get("research_data", [])
    collected = len(research_data)
    st.markdown(f"_Research process: collected {collected} sources in {duration:.1f}s._")

    # Research summary
    st.subheader("Research Summary")
    drafted = result.get("drafted_answer") or ""
    if drafted.strip():
        # Replace patterns like [Source: url1; url2] with compact [1], [2], ...
        # Hover shows full URLs; click opens the first URL.
        def compact_citations(text: str) -> str:
            pattern = re.compile(r"\[(?:Source|Sources?)\s*:\s*([^\]]+)\]", re.IGNORECASE)
            counter: int = 0
            seen: dict[tuple, int] = {}
            out_parts = []
            last = 0

            for m in pattern.finditer(text):
                # Append preceding text as-is (keep markdown)
                out_parts.append(text[last:m.start()])

                raw = m.group(1)
                # Split on ';' or ','
                urls = [u.strip() for u in re.split(r"[;,]", raw) if u.strip()]
                key = tuple(urls)
                if key in seen:
                    idx = seen[key]
                else:
                    counter += 1
                    idx = counter
                    seen[key] = idx

                first = urls[0] if urls else "#"
                title = "\n".join(urls) if urls else "No links provided"
                # Escape only attributes; keep outer markdown intact
                esc_first = first.replace('"', '&quot;')
                esc_title = title.replace('"', '&quot;')
                anchor = f'<a href="{esc_first}" target="_blank" title="{esc_title}">[{idx}]</a>'
                out_parts.append(anchor)

                last = m.end()

            out_parts.append(text[last:])
            return "".join(out_parts)

        processed = compact_citations(drafted)
        st.markdown(processed, unsafe_allow_html=True)
    else:
        st.info("No drafted answer returned.")

    # Research data
    st.subheader("Research Data")
    if not research_data:
        st.write("No research results found or there was an error during search.")
    else:
        # Show each result as a dropdown with link and concise snippet
        for i, item in enumerate(research_data, start=1):
            title = (item.get("title") or f"Result {i}").strip()
            url = (item.get("url") or "").strip()
            content = (item.get("content") or "").strip()
            domain = urlparse(url).netloc.replace("www.", "") if url else ""

            label = f"{i}. {title}" + (f" ({domain})" if domain else "")
            with st.expander(label):
                if url:
                    st.markdown(f"**Link:** [{title}]({url} \"{url}\")")
                if content:
                    # Strip markdown, normalize whitespace, clamp to fixed lines
                    snippet = strip_markdown(content)
                    snippet = " ".join(snippet.split())
                    if len(snippet) > SNIPPET_MAX_CHARS:
                        snippet = snippet[:SNIPPET_MAX_CHARS].rstrip() + "…"
                    st.markdown(
                        f'<div class="snippet-fixed">{html.escape(snippet)}</div>',
                        unsafe_allow_html=True,
                    )
                    if url:
                        st.markdown(f"[Read more]({url})")

    # Conclusion (true 1–2 sentence summary using LLM with fallback)
    @st.cache_data(show_spinner=False, ttl=3600)
    def summarize_to_two_sentences(text: str) -> str:
        prompt = (
            "Summarize the following content into 1-2 clear, simple sentences. "
            "No lists, no citations, no markdown. Focus on the key takeaway for a general user.\n\n"
            f"Content:\n{text}"
        )
        try:
            resp = llm.invoke(prompt)
            out = getattr(resp, "content", str(resp)).strip()
            parts = re.split(r"(?<=[.!?])\s+", out)
            short = " ".join(parts[:2]).strip()
            if len(short) > 320:
                short = short[:320].rstrip() + "…"
            return short or out
        except Exception:
            # Heuristic fallback: strip citations and compress to first 2 sentences
            tmp = re.sub(r"\[(?:Source|Sources?)\s*:\s*[^\]]+\]", "", text, flags=re.IGNORECASE)
            tmp = " ".join(tmp.split())
            parts = re.split(r"(?<=[.!?])\s+", tmp)
            short = " ".join(parts[:2]).strip()
            if len(short) > 320:
                short = short[:320].rstrip() + "…"
            return short

    st.subheader("Conclusion")
    if drafted.strip():
        st.write(summarize_to_two_sentences(drafted))
    else:
        st.write("No conclusion available.")
