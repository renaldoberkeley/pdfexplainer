from __future__ import annotations

from app.services.llm.base import PageContext


SYSTEM_INSTRUCTION = """You are an AI tutor helping a student understand a document.

Base your explanation on the supplied document pages.

Do not claim information is present in the document unless it actually appears in the supplied content.

Explain difficult concepts intuitively first, then provide technical detail.

For equations:
1. explain what the equation is trying to accomplish
2. define the important variables
3. explain the mathematical operation
4. give an intuitive interpretation

For diagrams and figures, explain their purpose and how their components relate.

If the supplied pages do not contain enough information to answer the question, say so."""


def build_prompt(*, question: str, pages: list[PageContext], include_image_markers: bool = False) -> str:
    grounded_pages: list[str] = []
    for page in pages:
        page_text = page.text.strip()
        marker = ""
        if include_image_markers and page.image is not None:
            marker = "\n[Rendered page image for this page is attached.]"
        grounded_pages.append(f"--- PAGE {page.page_number} ---\n{page_text}{marker}")

    document_content = "\n\n".join(grounded_pages)
    return (
        "INSTRUCTIONS:\n"
        f"{SYSTEM_INSTRUCTION}\n\n"
        "DOCUMENT CONTENT:\n"
        f"{document_content}\n\n"
        "USER QUESTION:\n"
        f"{question}\n\n"
        "EXPLANATION:"
    )
