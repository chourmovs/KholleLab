import asyncio
import hashlib
import json
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.logging import component_logger
from app.domain.problem import CurriculumInfo, Hint, Problem, ProblemGeneration, Skill, SourceInfo, Topic
from app.models.generated_problem import GeneratedProblem, GeneratedProblemStatus
from app.models.learning_session import LearningSession
from app.providers.llm import ModelRole
from app.schemas.problem_generation import GeneratedProblemDraft, ProblemGenerationCriticResult

GENERATOR_VERSION = "problem-generator-v1"
CRITIC_VERSION = "problem-critic-v1"
VALIDATION_VERSION = "problem-validation-v1"
URL_RE = re.compile(r"(?:https?://|www\.)", re.I)
ANSWER_LEAK_RE = re.compile(r"(?:réponse|solution)\s*[:=]", re.I)
_locks: dict[tuple[str, str, str, int], asyncio.Lock] = {}


def normalize_statement(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def content_hash(programme: str, level: str, expectation: str, difficulty: int,
                 statement: str, solution: str) -> str:
    canonical = json.dumps({"programme": programme, "level": level, "expectation": expectation,
        "difficulty": difficulty, "statement": normalize_statement(statement),
        "solution": normalize_statement(solution)}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def topic_for_domain(domain: str) -> Topic:
    aliases = {"numbers": Topic.ARITHMETIC, "data": Topic.PROBABILITY,
               "algorithmics": Topic.LOGIC, "automatismes": Topic.CALCULATION if hasattr(Topic, "CALCULATION") else Topic.ALGEBRA}
    try:
        return Topic(domain)
    except ValueError:
        return aliases.get(domain, Topic.ALGEBRA)


class GenerationUnavailable(RuntimeError):
    pass


class ProblemGenerationService:
    def __init__(self, catalog, curriculum, provider, config=settings):
        self.catalog, self.curriculum, self.provider, self.config = catalog, curriculum, provider, config
        prompts = Path(__file__).resolve().parents[1] / "prompts"
        self.generator_prompt = (prompts / "problem_generator_v1.md").read_text(encoding="utf-8")
        self.critic_prompt = (prompts / "problem_critic_v1.md").read_text(encoding="utf-8")
        self.log = component_logger("problem-generation")

    async def select(self, *, db, learner_id, level: str, expectation_id: str,
                     difficulty: int, domain: str | None = None):
        expectation = self.curriculum.expectations.get(expectation_id)
        if not expectation or expectation.level.value != level or expectation.historical:
            raise ValueError("expectation is not part of the active programme for this level")
        programme = self.curriculum.resolve_programme(level, self.catalog.static.academic_year)
        if expectation.programme_id != programme.id or (domain and expectation.domain != domain):
            raise ValueError("expectation does not match the trusted curriculum target")
        bucket = (programme.id, level, expectation.id, difficulty)
        rows = self.catalog.find_generated(programme_id=programme.id, level=level,
            expectation_id=expectation.id, difficulty=difficulty, domain=domain, db=db)
        seen = set(db.scalars(select(LearningSession.problem_id).where(LearningSession.learner_id == learner_id)))
        unseen = [row for row in rows if row.id not in seen]
        if unseen:
            self.log.info("generated_pool_hit expectation={} difficulty={} pool_size={} reused=true",
                          expectation.id, difficulty, len(rows))
            return self._serve(unseen[0], db), True
        # Between minimum and target, reuse rather than synchronously refill.
        if rows and len(rows) >= self.config.llm_problem_pool_min_available:
            self.log.info("generated_pool_hit expectation={} difficulty={} pool_size={} reused=true",
                          expectation.id, difficulty, len(rows))
            return self._serve(rows[0], db), True
        self.log.info("generated_pool_miss expectation={} difficulty={} pool_size={} reused=false",
                      expectation.id, difficulty, len(rows))
        if not self.config.llm_problem_generation_enabled:
            raise GenerationUnavailable("problem generation is disabled")
        lock = _locks.setdefault(bucket, asyncio.Lock())
        async with lock:
            # A concurrent request may have populated the global pool while waiting.
            refreshed = self.catalog.find_generated(programme_id=programme.id, level=level,
                expectation_id=expectation.id, difficulty=difficulty, domain=domain, db=db)
            concurrent = [row for row in refreshed if row.id not in seen]
            if concurrent:
                return self._serve(concurrent[0], db), True
            return await self._generate(db, programme.id, expectation, difficulty), False

    def _serve(self, row, db):
        self.catalog.mark_served(row.id, db)
        db.commit()
        self.log.info("generated_problem_served expectation={} difficulty={} pool_size={} reused=true",
                      row.expectation_id, row.difficulty, 1)
        return Problem.model_validate(row.payload_json)

    def _issues(self, draft, existing_statements):
        issues = []
        normalized = normalize_statement(draft.statement)
        if URL_RE.search(draft.statement) or URL_RE.search(draft.reference_solution): issues.append("external_url")
        if ANSWER_LEAK_RE.search(draft.statement): issues.append("answer_leak")
        if len(draft.statement) > 6000 or len(draft.reference_solution) > 10000: issues.append("excessive_length")
        for statement in existing_statements:
            other = normalize_statement(statement)
            if normalized == other: issues.append("exact_duplicate")
            elif SequenceMatcher(None, normalized, other).ratio() >= self.config.llm_problem_near_duplicate_threshold:
                issues.append("near_duplicate")
        return tuple(dict.fromkeys(issues))

    async def _generate(self, db, programme_id, expectation, difficulty):
        started = time.perf_counter()
        rows = self.catalog.find_generated(programme_id=programme_id, level=expectation.level.value,
            expectation_id=expectation.id, difficulty=difficulty, db=db)
        examples = self.catalog.list_static() + [Problem.model_validate(row.payload_json) for row in rows]
        same = [p for p in examples if expectation.id in p.curriculum.expectations]
        limited = same[:self.config.llm_problem_diversity_context_limit]
        diversity = [{"title": p.title, "statement": p.statement,
                      "archetype": p.generation.family_id if p.generation else "curated"} for p in limited]
        nodes = [self.curriculum.knowledge_nodes[k] for k in expectation.knowledge_ids]
        context = {"language": "fr", "level": expectation.level.value, "expectation_label": expectation.label,
            "expectation_description": expectation.description, "difficulty": difficulty,
            "knowledge": [{"id": n.id, "label": n.label} for n in nodes],
            "prerequisites": sorted({x for n in nodes for x in n.prerequisites}), "existing_examples": diversity}
        self.log.info("generation_started expectation={} difficulty={} pool_size={}", expectation.id, difficulty, len(rows))
        for attempt in range(1, self.config.llm_problem_max_generation_attempts + 1):
            draft = await self.provider.structured_response(instructions=self.generator_prompt,
                input_text=json.dumps(context, ensure_ascii=False), response_model=GeneratedProblemDraft,
                role=ModelRole.DEEP, family=self.config.llm_problem_generator_family)
            canonical_row = next((row for row in rows if normalize_statement(
                Problem.model_validate(row.payload_json).statement) == normalize_statement(draft.statement)), None)
            if canonical_row:
                return self._serve(canonical_row, db)
            issues = self._issues(draft, [p.statement for p in self.catalog.list_static()] +
                                  [Problem.model_validate(row.payload_json).statement for row in rows])
            if issues:
                self.log.info("generation_rejected expectation={} difficulty={} issue_codes={} attempt={}", expectation.id, difficulty, issues, attempt)
                continue
            critic_input = {"trusted_target": context, "draft": draft.model_dump()}
            critic = await self.provider.structured_response(instructions=self.critic_prompt,
                input_text=json.dumps(critic_input, ensure_ascii=False), response_model=ProblemGenerationCriticResult,
                role=ModelRole.DEEP, family=self.config.llm_problem_critic_family)
            if not critic.accepted:
                self.log.info("generation_rejected expectation={} difficulty={} issue_codes={} attempt={}", expectation.id, difficulty, critic.issue_codes, attempt)
                continue
            digest = content_hash(programme_id, expectation.level.value, expectation.id, difficulty,
                                  draft.statement, draft.reference_solution)
            existing = db.scalar(select(GeneratedProblem).where(GeneratedProblem.content_hash == digest))
            if existing:
                return self._serve(existing, db)
            identifier = f"llm-{expectation.level.value}-{digest[:12]}"
            problem = Problem(id=identifier, title=draft.title, statement=draft.statement,
                reference_solution=draft.reference_solution,
                curriculum=CurriculumInfo(level=expectation.level, difficulty=difficulty, expectations=(expectation.id,)),
                topics=(topic_for_domain(expectation.domain),), prerequisites=expectation.knowledge_ids,
                skills=(Skill.REASONING,), estimated_minutes=draft.estimated_minutes,
                hints=tuple(Hint(level=i + 1, text=text) for i, text in enumerate(draft.hints)),
                source=SourceInfo(type="llm", name="Exercice KHOLLELAB"),
                generation=ProblemGeneration(kind="llm", family_id=draft.archetype, version=1,
                    parameter_identity=digest, prompt_version=GENERATOR_VERSION, validation_version=VALIDATION_VERSION))
            row = GeneratedProblem(id=identifier, content_hash=digest, status=GeneratedProblemStatus.ACCEPTED,
                payload_json=problem.model_dump(mode="json"), level=expectation.level.value, programme_id=programme_id,
                expectation_id=expectation.id, domain=expectation.domain, difficulty=difficulty,
                generator_family=self.config.llm_problem_generator_family.value, generator_model=getattr(self.provider, "model", "unknown"),
                generator_prompt_version=GENERATOR_VERSION, critic_family=self.config.llm_problem_critic_family.value,
                critic_model=getattr(self.provider, "model", "unknown"), critic_prompt_version=CRITIC_VERSION,
                validation_version=VALIDATION_VERSION, validation_json=critic.model_dump())
            try:
                db.add(row); db.commit()
            except IntegrityError:
                db.rollback()
                row = db.scalar(select(GeneratedProblem).where(GeneratedProblem.content_hash == digest))
                if row is None: raise
            self.log.info("generation_accepted expectation={} difficulty={} latency_ms={} issue_codes=[]",
                          expectation.id, difficulty, round((time.perf_counter() - started) * 1000, 1))
            return self._serve(row, db)
        self.log.warning("generation_failed expectation={} difficulty={} issue_codes=attempts_exhausted", expectation.id, difficulty)
        raise GenerationUnavailable("validated generation attempts exhausted")
