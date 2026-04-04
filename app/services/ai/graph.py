import json
import logging
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

from app.config import get_settings
from app.services.ai.factory import get_chat_service

logger = logging.getLogger(__name__)
settings = get_settings()

class SummaryState(TypedDict):
    jd_context: str
    cv_context: str
    notes_context: str
    current_summary: str
    draft_summary: str
    critic_feedback: str
    score: int
    iterations: int

async def draft_node(state: SummaryState):
    """Writes or rewrites the summary."""
    chat_service = get_chat_service()
    
    jd = state["jd_context"]
    cv = state["cv_context"]
    notes = state.get("notes_context", "")
    current = state.get("current_summary", "")
    feedback = state.get("critic_feedback", "")
    iterations = state.get("iterations", 0)
    
    system_prompt = (
        "You are an expert resume writer specializing in ATS and recruiter-friendly "
        "formatting. Write a professional summary that aligns with the job description, "
        "is action-oriented, results-focused, and grounded in the candidate's actual experience. "
        "Do NOT invent skills the candidate does not have."
    )
    
    user_prompt = f"JOB DESCRIPTION:\n{jd}\n\nCANDIDATE EXPERIENCE:\n{cv}\n{notes}\n"
    if current:
        user_prompt += f"\nCurrent Summary (use as base if provided):\n{current}\n"
        
    if feedback:
        user_prompt += f"\nWARNING! PREVIOUS DRAFT RECEIVED CRITIQUE:\n{feedback}\nPlease fix the issues above and rewrite the summary completely to get a better score."
        
    draft = await chat_service.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=settings.llm_model,
        temperature=0.4,
    )
    
    return {"draft_summary": draft, "iterations": iterations + 1}

async def critic_node(state: SummaryState):
    """Scores the draft and provides feedback if poor."""
    chat_service = get_chat_service()
    
    jd = state["jd_context"]
    cv = state["cv_context"]
    draft = state["draft_summary"]
    
    system_prompt = (
        "You are an expert technical recruiter and resume critic. "
        "Your job is to read a candidate's drafted summary and grade it against "
        "the job requirements and the candidate's actual experience. "
        "Check heavily for hallucinations (skills the candidate doesn't have) "
        "and relevance (the summary should push skills the JD wants). "
        "You must respond ONLY with a valid JSON object in the exact following format:\n"
        '{"score": <int 0 to 10>, "feedback": "<string: what to fix>"}'
    )
    
    user_prompt = f"JOB DESCRIPTION:\n{jd}\n\nCANDIDATE ACTUAL CV (GROUND TRUTH):\n{cv}\n\nDRAFTED SUMMARY FOR REVIEW:\n{draft}\n\nPlease critically evaluate and return the JSON."
    
    # Usually you'd set response_format={"type": "json_object"} if using OpenAI,
    # but since this runs across different providers, we rely on zero-shot prompting 
    # to extract json from plain text.
    response = await chat_service.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=settings.llm_model,
        temperature=0.0,
    )
    
    score = 10
    feedback = ""
    try:
        clean_text = response.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_text)
        score = int(parsed.get("score", 10))
        feedback = parsed.get("feedback", "")
    except Exception as e:
        logger.warning(f"Critic JSON parser failed: {e}. Raw: {response}")
        # Default pass if parsing fails, but pass the raw response as feedback
        feedback = response
        
    return {"score": score, "critic_feedback": feedback}

def should_continue(state: SummaryState) -> Literal["draft_node", "__end__"]:
    score = state.get("score", 0)
    iterations = state.get("iterations", 0)
    
    if score >= 8 or iterations >= 3:
        return "__end__"
    return "draft_node"

# Build LangGraph
workflow = StateGraph(SummaryState)

workflow.add_node("draft_node", draft_node)
workflow.add_node("critic_node", critic_node)

workflow.set_entry_point("draft_node")
workflow.add_edge("draft_node", "critic_node")
workflow.add_conditional_edges(
    "critic_node",
    should_continue,
    {
        "__end__": END,
        "draft_node": "draft_node"
    }
)

app_graph = workflow.compile()
