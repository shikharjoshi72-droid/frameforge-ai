"""Story-level analysis: reconcile chunk summaries into one validated analysis."""
from ai import prompts


def story_facts(scenes: list, pages: int) -> dict:
    counts = {}
    for s in scenes:
        for c in s["characters"]:
            counts[c] = counts.get(c, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    return {"scenes": len(scenes), "pages": pages,
            "top_characters": ", ".join(f"{n} ({c} scenes)" for n, c in top) or "n/a"}


def analyze_story(client, summaries: list, scenes: list, pages: int, page_basis: str = "actual") -> dict:
    try:
        from ai.schemas import StoryAnalysisAI
    except ImportError:
        StoryAnalysisAI = None
    if not summaries:
        raise ValueError("No chunk summaries available; run scene extraction first.")
    limit = 24000
    total = sum(len(s) for s in summaries)
    if total > limit:  # shrink proportionally rather than drop story sections
        per = max(200, limit // len(summaries))
        summaries = [s[:per] for s in summaries]
    facts = story_facts(scenes, pages)
    result = client.chat_json(prompts.story_prompt(summaries, facts), StoryAnalysisAI)
    # runtime: a defensible rule of thumb (1 script page ~ 1 minute), always labelled as an estimate
    result["runtime_estimate_min"] = pages
    result["runtime_basis"] = ("Rule of thumb: 1 screenplay page is about 1 minute of screen time"
                               + (" (page count estimated from line count)" if page_basis == "estimated" else "")
                               + ". Actual runtime will vary.")
    result["scene_count"] = len(scenes)
    result["page_count"] = pages
    return result
