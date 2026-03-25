"""CV/JD matching endpoints."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import rag
from app.services.ai.factory import get_chat_service
from app.services.document_ingestion import ingest_uploaded_file
from app.services.rag import ingest_document, similarity_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match", tags=["match"])


class CVJDMatchRequest:
    """Request schema for CV/JD matching."""

    def __init__(
        self,
        cv_id: str,
        jd_id: str,
        additional_notes: str | None = None,
    ):
        self.cv_id = cv_id
        self.jd_id = jd_id
        self.additional_notes = additional_notes


async def _cleanup_documents(db: AsyncSession, document_ids: list[uuid.UUID]) -> None:
    for document_id in document_ids:
        try:
            await rag.delete_document(db, document_id)
        except Exception:
            logger.exception("Failed to cleanup document id=%s after bundle upload error", document_id)


async def _get_document_or_404(db: AsyncSession, document_id: str, *, label: str):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {label}_id",
        ) from exc

    document = await rag.get_document(db, parsed_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label.upper()} document not found",
        )
    return document


async def _get_optional_document(
    db: AsyncSession,
    document_id: str | None,
    *,
    label: str,
):
    if not document_id:
        return None
    return await _get_document_or_404(db, document_id, label=label)


def _notes_context(notes_document) -> str:
    if notes_document is None:
        return ""
    return f"\n\nADDITIONAL NOTES:\n{notes_document.content}"


@router.post("/upload-documents")
async def upload_cv_and_jd(
    cv_content: str,
    jd_content: str,
    notes_content: str | None = None,
    cv_title: str = "Resume",
    jd_title: str = "Job Description",
    notes_title: str = "Application Notes",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload CV and JD documents for matching.

    Returns: {"cv_id": str, "jd_id": str}
    """
    created_ids: list[uuid.UUID] = []
    try:
        cv_doc = await ingest_document(
            db,
            title=cv_title,
            content=cv_content,
            metadata={"type": "cv"},
            doc_type="cv",
            use_chunking=True,
        )
        created_ids.append(cv_doc.id)

        jd_doc = await ingest_document(
            db,
            title=jd_title,
            content=jd_content,
            metadata={"type": "jd"},
            doc_type="jd",
            use_chunking=True,
        )
        created_ids.append(jd_doc.id)

        notes_id = None
        if notes_content and notes_content.strip():
            notes_doc = await ingest_document(
                db,
                title=notes_title,
                content=notes_content.strip(),
                metadata={"type": "notes"},
                doc_type="notes",
                use_chunking=True,
            )
            created_ids.append(notes_doc.id)
            notes_id = str(notes_doc.id)

        return {"cv_id": str(cv_doc.id), "jd_id": str(jd_doc.id), "notes_id": notes_id}
    except Exception:
        await _cleanup_documents(db, created_ids)
        raise


@router.post("/upload-bundle", status_code=status.HTTP_201_CREATED)
async def upload_bundle(
    cv_file: Annotated[UploadFile, File(description="CV file (.pdf, .txt, .md)")],
    jd_file: Annotated[UploadFile, File(description="JD file (.pdf, .txt, .md)")],
    notes: Annotated[str | None, Form(description="Optional recruiter or user notes")] = None,
    cv_title: Annotated[str, Form(min_length=1, max_length=512)] = "Resume",
    jd_title: Annotated[str, Form(min_length=1, max_length=512)] = "Job Description",
    notes_title: Annotated[str, Form(min_length=1, max_length=512)] = "Application Notes",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a CV file, a JD file, and optional notes in one request."""
    created_ids: list[uuid.UUID] = []
    try:
        cv_doc = await ingest_uploaded_file(
            db,
            cv_file,
            title=cv_title,
            doc_type="cv",
            metadata={"type": "cv"},
            use_chunking=True,
        )
        created_ids.append(cv_doc.id)

        jd_doc = await ingest_uploaded_file(
            db,
            jd_file,
            title=jd_title,
            doc_type="jd",
            metadata={"type": "jd"},
            use_chunking=True,
        )
        created_ids.append(jd_doc.id)

        notes_id = None
        if notes and notes.strip():
            notes_doc = await ingest_document(
                db,
                title=notes_title,
                content=notes.strip(),
                metadata={"type": "notes"},
                doc_type="notes",
                use_chunking=True,
            )
            created_ids.append(notes_doc.id)
            notes_id = str(notes_doc.id)

        return {
            "cv_id": str(cv_doc.id),
            "jd_id": str(jd_doc.id),
            "notes_id": notes_id,
        }
    except Exception:
        await _cleanup_documents(db, created_ids)
        raise


@router.post("/analyze-cv/{document_id}")
async def analyze_cv(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full analysis of a CV."""
    return {"status": "ok", "document_id": document_id}


@router.post("/missing-skills")
async def find_missing_skills(
    cv_id: str,
    jd_id: str,
    notes_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Analyze which skills from JD are missing in CV.

    Returns: {"missing_skills": list[str], "sources": list[SearchResult]}
    """
    cv_document = await _get_document_or_404(db, cv_id, label="cv")
    jd_document = await _get_document_or_404(db, jd_id, label="jd")
    notes_document = await _get_optional_document(db, notes_id, label="notes")

    # Find skill-related chunks in JD
    jd_skill_results = await similarity_search(
        db,
        query="What skills and qualifications are required?",
        top_k=5,
        document_ids=[jd_document.id],
    )

    # Find what the CV mentions
    cv_skill_results = await similarity_search(
        db,
        query="What technical skills, programming languages, tools, and competencies?",
        top_k=5,
        document_ids=[cv_document.id],
    )

    chat_service = get_chat_service()

    # Ask LLM to identify missing skills
    jd_skills_text = "\n".join([r.content for r in jd_skill_results])
    cv_skills_text = "\n".join([r.content for r in cv_skill_results])

    system_prompt = (
        "You are an expert career coach. Analyze the job description skills and the CV "
        "skills provided. Identify which skills from the job description are missing "
        "or weak in the CV. Return a concise list of skills that should be highlighted, "
        "learned, or emphasized."
    )

    user_prompt = f"""
JOB DESCRIPTION SKILLS & REQUIREMENTS:
{jd_skills_text}

CV SKILLS:
{cv_skills_text}
{_notes_context(notes_document)}

What skills are missing from the CV compared to the job description?
List them as a comma-separated list with brief explanations."""

    missing_skills_analysis = await chat_service.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model="llama-3.1-8b-instant",
        temperature=0.3,
    )

    return {
        "missing_skills": missing_skills_analysis,
        "jd_skills_sources": [r.model_dump() for r in jd_skill_results],
        "cv_skills_sources": [r.model_dump() for r in cv_skill_results],
    }


@router.post("/rewrite-summary")
async def rewrite_summary(
    cv_id: str,
    jd_id: str,
    notes_id: str | None = None,
    current_summary: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Rewrite CV summary to match job description.

    Returns: {"new_summary": str, "sources": list[SearchResult]}
    """
    cv_document = await _get_document_or_404(db, cv_id, label="cv")
    jd_document = await _get_document_or_404(db, jd_id, label="jd")
    notes_document = await _get_optional_document(db, notes_id, label="notes")

    # Get JD requirements
    jd_results = await similarity_search(
        db,
        query="What are the main responsibilities and requirements for this role?",
        top_k=3,
        document_ids=[jd_document.id],
    )

    # Get CV experience
    cv_results = await similarity_search(
        db,
        query="Professional experience, accomplishments, background",
        top_k=3,
        document_ids=[cv_document.id],
    )

    jd_text = "\n".join([r.content for r in jd_results])
    cv_experience = "\n".join([r.content for r in cv_results])

    chat_service = get_chat_service()

    system_prompt = (
        "You are an expert resume writer specializing in ATS and recruiter-friendly "
        "formatting. Rewrite the professional summary so it is concise, aligned with "
        "the job description, action-oriented, results-focused, and grounded in the "
        "candidate's real experience."
    )

    user_prompt = f"""
JOB DESCRIPTION:
{jd_text}

CANDIDATE'S BACKGROUND:
{cv_experience}
{_notes_context(notes_document)}

Current summary (if any): {current_summary or "No existing summary"}

Please rewrite the professional summary to match this job description while staying
true to the candidate's actual experience."""

    new_summary = await chat_service.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model="llama-3.1-8b-instant",
        temperature=0.4,
    )

    return {
        "new_summary": new_summary,
        "jd_sources": [r.model_dump() for r in jd_results],
        "cv_sources": [r.model_dump() for r in cv_results],
    }


@router.post("/highlight-achievements")
async def highlight_achievements(
    cv_id: str,
    jd_id: str,
    notes_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Identify which achievements to highlight for this job.

    Returns: {"achievements_to_highlight": str, "sources": list[SearchResult]}
    """
    cv_document = await _get_document_or_404(db, cv_id, label="cv")
    jd_document = await _get_document_or_404(db, jd_id, label="jd")
    notes_document = await _get_optional_document(db, notes_id, label="notes")

    # Get JD key requirements
    jd_results = await similarity_search(
        db,
        query="Key responsibilities, desired outcomes, business impact",
        top_k=5,
        document_ids=[jd_document.id],
    )

    # Get CV achievements
    cv_results = await similarity_search(
        db,
        query="achievements, accomplishments, projects completed, impact, results, metrics",
        top_k=5,
        document_ids=[cv_document.id],
    )

    jd_text = "\n".join([r.content for r in jd_results])
    cv_achievements = "\n".join([r.content for r in cv_results])

    chat_service = get_chat_service()

    system_prompt = """You are an expert recruiter and career coach.
Analyze the candidate's achievements and the job requirements.
Identify which 3-5 achievements are MOST RELEVANT to this specific job.
Explain WHY each achievement matters for this role.
Format as a clear, actionable list."""

    user_prompt = f"""
JOB REQUIREMENTS:
{jd_text}

CANDIDATE'S ACHIEVEMENTS & PROJECTS:
{cv_achievements}
{_notes_context(notes_document)}

Which achievements should this candidate highlight for this position? Explain the connection to the job requirements."""

    achievements_to_highlight = await chat_service.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model="llama-3.1-8b-instant",
        temperature=0.3,
    )

    return {
        "achievements_to_highlight": achievements_to_highlight,
        "jd_sources": [r.model_dump() for r in jd_results],
        "cv_sources": [r.model_dump() for r in cv_results],
    }
