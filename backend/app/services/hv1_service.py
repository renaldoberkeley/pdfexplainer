from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import yaml
from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.evaluation.models import (
    HumanAssignment,
    HumanParticipant,
    HumanRating,
    HumanStudy,
)
from app.models.hv1_schemas import (
    Hv1CalibrationExample,
    Hv1PageSource,
    Hv1Progress,
    Hv1ProgressResponse,
    Hv1RatingSubmitRequest,
    Hv1RatingSubmitResponse,
    Hv1RubricCriterion,
    Hv1RubricSummary,
    Hv1SessionStartRequest,
    Hv1SessionStartResponse,
    Hv1TaskPayload,
    Hv1TaskResponse,
)

DEFAULT_STUDY_ID = "hv1_e2_human_validation"
DEFAULT_ASSIGNMENT_VERSION = "hv1-assignment-v1"
DEFAULT_SLOT_COUNT = 6
DEFAULT_RENDER_DPI = 150


@dataclass(slots=True)
class Hv1ResponseRecord:
    hv1_response_id: str
    family_id: str
    document: str
    pages: list[int]
    question: str
    answer: str
    is_visual_case: bool
    condition: str


class HV1Service:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        data_dir: Path,
        document_dir: Path,
        rubric_file: Path,
        study_spec_file: Path,
    ) -> None:
        self._session_factory = session_factory
        self._data_dir = data_dir
        self._document_dir = document_dir
        self._rubric_file = rubric_file
        self._study_spec_file = study_spec_file
        self._hash_salt = os.getenv("HV1_ID_HASH_SALT", "hv1-local-dev-salt")

        self._response_pool = self._load_response_pool()
        self._responses_by_id = {item.hv1_response_id: item for item in self._response_pool}
        self._families = self._build_family_index()
        self._study_spec = self._load_study_spec()
        self._rubric = self._load_rubric()
        self._calibration = self._load_calibration()
        self._intro_notice = (
            "DRAFT — REQUIRES PRE-LAUNCH ETHICS/IRB REVIEW. "
            "Do not recruit participants or collect real ratings yet."
        )

    @property
    def study_id(self) -> str:
        return str(self._study_spec.get("study_id", DEFAULT_STUDY_ID))

    def start_session(self, payload: Hv1SessionStartRequest) -> Hv1SessionStartResponse:
        with self._session_factory() as session:
            study = self._ensure_study_row(session)
            provider, ext_hashes = self._resolve_provider_and_hashes(payload)
            participant = self._find_existing_participant(session, study.id, provider, ext_hashes)
            if participant is None:
                participant = self._create_participant(session, study.id, provider, ext_hashes)
                self._create_assignments_for_participant(session, participant, study.assignment_version)

            session.flush()
            participant_session_id = participant.public_id
            progress = self._progress_for_participant(session, participant.id)
            next_task = self._next_task_for_participant(session, participant.id)
            session.commit()

        return Hv1SessionStartResponse(
            participant_session_id=participant_session_id,
            provider=provider,
            progress=progress,
            next_task=next_task,
            rubric=self._rubric,
            calibration_example=self._calibration,
            intro_notice=self._intro_notice,
        )

    def get_progress(self, participant_session_id: str) -> Hv1ProgressResponse:
        with self._session_factory() as session:
            participant = self._participant_by_public_id(session, participant_session_id)
            progress = self._progress_for_participant(session, participant.id)
        return Hv1ProgressResponse(participant_session_id=participant_session_id, progress=progress)

    def get_next_task(self, participant_session_id: str) -> Hv1TaskResponse:
        with self._session_factory() as session:
            participant = self._participant_by_public_id(session, participant_session_id)
            progress = self._progress_for_participant(session, participant.id)
            next_task = self._next_task_for_participant(session, participant.id)
        return Hv1TaskResponse(
            participant_session_id=participant_session_id,
            progress=progress,
            next_task=next_task,
        )

    def submit_rating(
        self, participant_session_id: str, payload: Hv1RatingSubmitRequest
    ) -> Hv1RatingSubmitResponse:
        with self._session_factory() as session:
            participant = self._participant_by_public_id(session, participant_session_id)
            assignment = self._assignment_for_participant_response(
                session, participant.id, payload.hv1_response_id
            )
            if assignment is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned response not found for this participant.",
                )
            existing = session.execute(
                select(HumanRating).where(HumanRating.assignment_id == assignment.id)
            ).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This response has already been rated.",
                )

            response_record = self._responses_by_id.get(payload.hv1_response_id)
            if response_record is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unknown response identifier.",
                )

            if response_record.is_visual_case:
                if payload.visual_grounding is None or payload.visual_detail_accuracy is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            "Visual criteria are required for this task because the prompt "
                            "includes visual source material."
                        ),
                    )
            else:
                if payload.visual_grounding is not None or payload.visual_detail_accuracy is not None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Visual criteria must be empty for non-visual tasks.",
                    )

            session.add(
                HumanRating(
                    study_id=participant.study_id,
                    participant_id=participant.id,
                    assignment_id=assignment.id,
                    hv1_response_id=payload.hv1_response_id,
                    rubric_version=self._rubric.rubric_version,
                    factual_correctness=payload.factual_correctness,
                    document_grounding=payload.document_grounding,
                    completeness=payload.completeness,
                    teaching_clarity=payload.teaching_clarity,
                    visual_grounding=payload.visual_grounding,
                    visual_detail_accuracy=payload.visual_detail_accuracy,
                    comment=payload.comment,
                    is_test_data=participant.external_provider != "prolific",
                )
            )

            progress_after = self._progress_for_participant(session, participant.id, include_pending=True)
            if progress_after.remaining == 0 and participant.completed_at is None:
                participant.status = "completed"
                participant.completed_at = datetime.now(timezone.utc)

            session.flush()
            progress = self._progress_for_participant(session, participant.id)
            next_task = self._next_task_for_participant(session, participant.id)
            session.commit()

        return Hv1RatingSubmitResponse(
            participant_session_id=participant_session_id,
            saved=True,
            progress=progress,
            next_task=next_task,
        )

    def _ensure_study_row(self, session: Session) -> HumanStudy:
        row = session.execute(
            select(HumanStudy).where(HumanStudy.study_id == self.study_id)
        ).scalar_one_or_none()
        if row is not None:
            return row

        row = HumanStudy(
            study_id=self.study_id,
            protocol_version=str(self._study_spec.get("protocol_version", "hv1-protocol-v1")),
            rubric_version=str(self._study_spec["rubric_version"]),
            source_results_commit=str(self._study_spec["source_results_commit"]),
            source_experiment=str(self._study_spec.get("source_experiment", "E2")),
            status=str(self._study_spec["status"]),
            participant_source=str(self._study_spec["participant_source"]),
            responses=int(self._study_spec["responses"]),
            ratings_per_response=int(self._study_spec["ratings_per_response"]),
            target_total_ratings=int(self._study_spec["target_total_ratings"]),
            assignment_version=str(
                self._study_spec.get("assignment_version", DEFAULT_ASSIGNMENT_VERSION)
            ),
            randomization_seed=str(self._study_spec.get("randomization_seed", "hv1-seed-20261004")),
            metadata_json={
                "notes": "HV1 preregistered local research instrument. Not launched.",
                "ethics_checkpoint": "unresolved_prelaunch",
            },
        )
        session.add(row)
        session.flush()
        return row

    def _resolve_provider_and_hashes(
        self, payload: Hv1SessionStartRequest
    ) -> tuple[str, tuple[str | None, str | None, str | None]]:
        if payload.prolific_pid:
            provider = "prolific"
            return (
                provider,
                (
                    self._hash_value(payload.prolific_pid),
                    self._hash_value(payload.study_id),
                    self._hash_value(payload.session_id),
                ),
            )
        provider = "development"
        label = payload.local_participant_label or f"local-{uuid.uuid4()}"
        return provider, (self._hash_value(label), None, None)

    def _find_existing_participant(
        self,
        session: Session,
        study_pk: int,
        provider: str,
        external_hashes: tuple[str | None, str | None, str | None],
    ) -> HumanParticipant | None:
        participant_hash, study_hash, session_hash = external_hashes
        if participant_hash is None:
            return None
        stmt: Select[tuple[HumanParticipant]] = select(HumanParticipant).where(
            HumanParticipant.study_id == study_pk,
            HumanParticipant.external_provider == provider,
            HumanParticipant.external_participant_hash == participant_hash,
        )
        if study_hash is not None:
            stmt = stmt.where(HumanParticipant.external_study_hash == study_hash)
        if session_hash is not None:
            stmt = stmt.where(HumanParticipant.external_session_hash == session_hash)
        return session.execute(stmt).scalar_one_or_none()

    def _create_participant(
        self,
        session: Session,
        study_pk: int,
        provider: str,
        external_hashes: tuple[str | None, str | None, str | None],
    ) -> HumanParticipant:
        count = session.execute(
            select(func.count()).select_from(HumanParticipant).where(HumanParticipant.study_id == study_pk)
        ).scalar_one()
        slot = int(count) % DEFAULT_SLOT_COUNT
        participant = HumanParticipant(
            study_id=study_pk,
            public_id=str(uuid.uuid4()),
            external_provider=provider,
            external_participant_hash=external_hashes[0],
            external_study_hash=external_hashes[1],
            external_session_hash=external_hashes[2],
            assignment_slot=slot,
            assignment_version=str(
                self._study_spec.get("assignment_version", DEFAULT_ASSIGNMENT_VERSION)
            ),
            status="in_progress",
        )
        session.add(participant)
        session.flush()
        return participant

    def _create_assignments_for_participant(
        self, session: Session, participant: HumanParticipant, assignment_version: str
    ) -> None:
        random_seed = str(self._study_spec.get("randomization_seed", "hv1-seed-20261004"))
        chosen_ids: list[str] = []
        for family_idx, family_id in enumerate(sorted(self._families.keys())):
            pair = sorted(self._families[family_id], key=lambda item: item.condition)
            if len(pair) != 2:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Family {family_id} does not have exactly two responses.",
                )
            # Balanced across 6 slots: each family gets 3 text + 3 text_image ratings.
            selected_index = (participant.assignment_slot + family_idx) % 2
            chosen_ids.append(pair[selected_index].hv1_response_id)

        randomizer = random.Random(f"{random_seed}:{participant.assignment_slot}")
        randomizer.shuffle(chosen_ids)

        for order, response_id in enumerate(chosen_ids, start=1):
            response_record = self._responses_by_id[response_id]
            session.add(
                HumanAssignment(
                    study_id=participant.study_id,
                    participant_id=participant.id,
                    hv1_response_id=response_id,
                    family_id=response_record.family_id,
                    task_order=order,
                    assignment_version=assignment_version,
                )
            )

    def _progress_for_participant(
        self, session: Session, participant_id: int, *, include_pending: bool = False
    ) -> Hv1Progress:
        total = session.execute(
            select(func.count()).select_from(HumanAssignment).where(HumanAssignment.participant_id == participant_id)
        ).scalar_one()
        completed = session.execute(
            select(func.count()).select_from(HumanRating).where(HumanRating.participant_id == participant_id)
        ).scalar_one()
        remaining = max(int(total) - int(completed), 0)
        percent = round((int(completed) / int(total) * 100.0), 2) if total else 0.0
        if include_pending:
            session.flush()
        return Hv1Progress(
            completed=int(completed),
            total=int(total),
            remaining=remaining,
            completed_percent=percent,
        )

    def _next_task_for_participant(self, session: Session, participant_id: int) -> Hv1TaskPayload | None:
        assignment = session.scalars(
            select(HumanAssignment)
            .where(HumanAssignment.participant_id == participant_id)
            .where(~HumanAssignment.id.in_(select(HumanRating.assignment_id)))
            .order_by(HumanAssignment.task_order.asc())
            .limit(1)
        ).first()
        if assignment is None:
            return None
        record = self._responses_by_id[assignment.hv1_response_id]
        page_sources = self._build_page_sources(record.document, record.pages)
        return Hv1TaskPayload(
            hv1_response_id=record.hv1_response_id,
            is_visual_case=record.is_visual_case,
            question=record.question,
            answer=record.answer,
            source_document=record.document,
            source_pages=page_sources,
        )

    def _assignment_for_participant_response(
        self, session: Session, participant_id: int, hv1_response_id: str
    ) -> HumanAssignment | None:
        return session.execute(
            select(HumanAssignment).where(
                HumanAssignment.participant_id == participant_id,
                HumanAssignment.hv1_response_id == hv1_response_id,
            )
        ).scalar_one_or_none()

    def _participant_by_public_id(self, session: Session, public_id: str) -> HumanParticipant:
        participant = session.execute(
            select(HumanParticipant).where(HumanParticipant.public_id == public_id)
        ).scalar_one_or_none()
        if participant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant session was not found.",
            )
        return participant

    def _build_page_sources(self, document: str, pages: list[int]) -> list[Hv1PageSource]:
        pdf_path = self._document_dir / document
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Source document not found for task: {document}",
            )

        page_sources: list[Hv1PageSource] = []
        with fitz.open(pdf_path) as pdf:
            for page_number in pages:
                if page_number < 1 or page_number > pdf.page_count:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Invalid page {page_number} for source document {document}.",
                    )
                page = pdf.load_page(page_number - 1)
                pixmap = page.get_pixmap(dpi=DEFAULT_RENDER_DPI, alpha=False)
                image_bytes = pixmap.tobytes("png")
                page_sources.append(
                    Hv1PageSource(
                        page_number=page_number,
                        image_base64=base64.b64encode(image_bytes).decode("ascii"),
                        image_mime_type="image/png",
                        extracted_text=page.get_text("text"),
                        width=int(pixmap.width),
                        height=int(pixmap.height),
                    )
                )
        return page_sources

    def _load_response_pool(self) -> list[Hv1ResponseRecord]:
        public_rows = json.loads((self._data_dir / "hv1_response_pool_public.json").read_text())
        private_rows = json.loads((self._data_dir / "hv1_private_mapping.secure.json").read_text())
        private_by = {row["hv1_response_id"]: row for row in private_rows}
        records: list[Hv1ResponseRecord] = []
        for row in public_rows:
            private = private_by.get(row["hv1_response_id"])
            if private is None:
                raise RuntimeError(f"Missing private mapping for {row['hv1_response_id']}")
            records.append(
                Hv1ResponseRecord(
                    hv1_response_id=row["hv1_response_id"],
                    family_id=row["family_id"],
                    document=row["document"],
                    pages=[int(page) for page in row["pages"]],
                    question=row["question"],
                    answer=row["answer"],
                    is_visual_case=bool(row["is_visual_case"]),
                    condition=str(private["condition"]),
                )
            )
        return records

    def _build_family_index(self) -> dict[str, list[Hv1ResponseRecord]]:
        index: dict[str, list[Hv1ResponseRecord]] = {}
        for record in self._response_pool:
            index.setdefault(record.family_id, []).append(record)
        return index

    def _load_rubric(self) -> Hv1RubricSummary:
        parsed = yaml.safe_load(self._rubric_file.read_text())
        return Hv1RubricSummary(
            rubric_version=str(parsed["rubric_version"]),
            abstention_policy=str(parsed["abstention_policy"]),
            criteria=[
                Hv1RubricCriterion(
                    name=str(item["name"]),
                    applies_to=str(item["applies_to"]),
                    anchors={str(key): str(value) for key, value in item["anchors"].items()},
                )
                for item in parsed["criteria"]
            ],
        )

    def _load_study_spec(self) -> dict[str, Any]:
        return dict(yaml.safe_load(self._study_spec_file.read_text()))

    def _load_calibration(self) -> Hv1CalibrationExample:
        return Hv1CalibrationExample.model_validate(
            json.loads((self._data_dir / "hv1_calibration_fixture.json").read_text())
        )

    def _hash_value(self, value: str | None) -> str | None:
        if value is None:
            return None
        digest = hashlib.sha256(f"{self._hash_salt}::{value}".encode("utf-8")).hexdigest()
        return digest
