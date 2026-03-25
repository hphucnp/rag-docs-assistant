"""Semantic text chunking for documents."""

import re
from typing import NamedTuple


class Chunk(NamedTuple):
    """Represents a chunk of text with optional metadata."""

    text: str
    start_idx: int
    end_idx: int
    section: str | None = None


def semantic_chunk(
    text: str,
    chunk_size: int = 400,
    overlap: int = 50,
    section_name: str | None = None,
) -> list[Chunk]:
    """
    Split text into semantic chunks by sentences with configurable overlap.

    Args:
        text: Input text to chunk
        chunk_size: Target number of tokens per chunk (approximate)
        overlap: Number of tokens to overlap between chunks
        section_name: Optional section identifier

    Returns:
        List of Chunk objects with position and section info
    """
    # Split by sentences (., !, ?)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    chunks: list[Chunk] = []
    current_chunk: list[str] = []
    current_tokens = 0
    chunk_start_idx = 0

    for sentence in sentences:
        # Rough token estimate: 1 token ≈ 4 characters
        sentence_tokens = len(sentence) // 4 + 1

        # If adding this sentence exceeds chunk_size, save current chunk
        if current_tokens + sentence_tokens > chunk_size and current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_end_idx = chunk_start_idx + len(chunk_text)

            chunks.append(
                Chunk(
                    text=chunk_text,
                    start_idx=chunk_start_idx,
                    end_idx=chunk_end_idx,
                    section=section_name,
                )
            )

            # Start new chunk with overlap (last sentence(s) repeated)
            overlap_tokens = 0
            overlap_sentences = []

            for prev_sent in reversed(current_chunk):
                prev_tokens = len(prev_sent) // 4 + 1
                if overlap_tokens + prev_tokens <= overlap:
                    overlap_sentences.insert(0, prev_sent)
                    overlap_tokens += prev_tokens
                else:
                    break

            current_chunk = overlap_sentences
            current_tokens = overlap_tokens
            chunk_start_idx = chunk_end_idx - len(" ".join(overlap_sentences))

        current_chunk.append(sentence)
        current_tokens += sentence_tokens

    # Add final chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunk_end_idx = chunk_start_idx + len(chunk_text)
        chunks.append(
            Chunk(
                text=chunk_text,
                start_idx=chunk_start_idx,
                end_idx=chunk_end_idx,
                section=section_name,
            )
        )

    return chunks


def extract_cv_sections(text: str) -> dict[str, str]:
    """
    Extract common CV sections from text.

    Returns a dict mapping section name (lowercase) to section content.
    """
    sections = {}

    # Common CV section headers
    section_patterns = {
        "contact": r"(?i)^(contact|personal info|information).*?(?=^(?:summary|objective|skills|experience|education|certifications|languages|interests))",
        "summary": r"(?i)^(summary|objective|profile|professional summary).*?(?=^(?:skills|experience|education))",
        "skills": r"(?i)^(skills|technical skills|competencies|expertise).*?(?=^(?:experience|education|projects|certifications))",
        "experience": r"(?i)^(experience|work experience|employment|professional experience).*?(?=^(?:education|projects|skills|certifications))",
        "education": r"(?i)^(education|qualifications|academic).*?(?=^(?:experience|projects|skills|certifications|languages))",
        "projects": r"(?i)^(projects|portfolio|case studies).*?(?=^(?:experience|skills|certifications|languages))",
        "certifications": r"(?i)^(certifications|certificates|awards|licenses).*?(?=^(?:experience|education|languages|interests))",
        "languages": r"(?i)^(languages?).*?(?=^(?:experience|education|interests|skills))",
    }

    for section_name, pattern in section_patterns.items():
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            sections[section_name] = match.group(0).strip()

    # If no sections matched, treat entire text as one section
    if not sections:
        sections["content"] = text

    return sections


def extract_jd_sections(text: str) -> dict[str, str]:
    """
    Extract common Job Description sections from text.

    Returns a dict mapping section name (lowercase) to section content.
    """
    sections = {}

    section_patterns = {
        "title": r"(?i)^(job title|position|role).*?(?=^(?:summary|about|description|responsibilities))",
        "about": r"(?i)^(about|company|about the company|overview).*?(?=^(?:responsibilities|requirements|skills))",
        "summary": r"(?i)^(summary|overview|description|job description|overview).*?(?=^(?:responsibilities|requirements|qualifications))",
        "responsibilities": r"(?i)^(responsibilities|duties|what you'll do|what we're looking for).*?(?=^(?:requirements|qualifications|skills|benefits))",
        "requirements": r"(?i)^(requirements|required|must have|qualifications).*?(?=^(?:nice-to-have|benefits|skills|experience|compensation))",
        "nice_to_have": r"(?i)^(nice.?to.?have|preferred|desired|bonus).*?(?=^(?:requirements|benefits|compensation|experience))",
        "benefits": r"(?i)^(benefits?|compensation|salary|perks).*?(?=^(?:experience|qualifications))",
    }

    for section_name, pattern in section_patterns.items():
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            sections[section_name] = match.group(0).strip()

    if not sections:
        sections["content"] = text

    return sections


def chunk_by_sections(
    text: str,
    doc_type: str = "cv",
    chunk_size: int = 400,
) -> list[Chunk]:
    """
    Chunk text by document sections (CV or JD).

    Args:
        text: Input document text
        doc_type: "cv" or "jd"
        chunk_size: Token size per semantic chunk within section

    Returns:
        List of chunks with section metadata
    """
    all_chunks: list[Chunk] = []

    normalized_doc_type = doc_type.lower()

    if normalized_doc_type == "cv":
        sections = extract_cv_sections(text)
    elif normalized_doc_type == "jd":
        sections = extract_jd_sections(text)
    else:
        sections = {normalized_doc_type or "content": text}

    for section_name, section_content in sections.items():
        # Chunk each section separately
        section_chunks = semantic_chunk(
            section_content, chunk_size=chunk_size, section_name=section_name
        )
        all_chunks.extend(section_chunks)

    return all_chunks
