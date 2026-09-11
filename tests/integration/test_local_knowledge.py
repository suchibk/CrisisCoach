from datetime import date
import pytest
from pydantic import ValidationError
from crisis_coach import CollisionWorkflow, SessionStatus
from crisis_coach.models.knowledge import KnowledgeContext, KnowledgeQuery, SourceCorpus, SourcePassage, KnowledgeAnswer
from crisis_coach.models.events import ContextEvent, QuestionEvent
from crisis_coach.knowledge.local import LocalKnowledgeRetriever
from crisis_coach.guardrails.grounding import validate_grounding
from crisis_coach.tools.capture import build_capture_executor
from crisis_coach.persistence.sqlite import SQLiteIncidentRepository

@pytest.fixture
def scene(tmp_path, monkeypatch):
    monkeypatch.delenv("CRISIS_COACH_KNOWLEDGE_DIR", raising=False)
    repo = SQLiteIncidentRepository(tmp_path / "incidents.db")
    coach = CollisionWorkflow(repository=repo, executor=build_capture_executor(tmp_path / "attachments"))
    state, _ = coach.start()
    for answer in ("No", "No", "Yes"): coach.turn(state, answer)
    return coach, state, repo


def test_missing_context_never_guesses_danas_policy(scene):
    coach, state, _ = scene
    reply = coach.turn(state, "/ask What is my excess?")
    assert not reply.citations
    assert state.knowledge_answers[-1].status == "not_found"


def test_demo_citations_preserve_task_timer_and_survive_restart(scene):
    coach, state, repo = scene
    current, timer = state.last_instruction, state.timer_deadline
    coach.turn(state, "/knowledge-demo")
    reply = coach.turn(state, "How long do I have to notify my insurer?")
    assert "SYNTHETIC DEMO" in reply.text and "24 hours" in reply.text
    assert reply.citations[0].section == "7.2"
    assert state.last_instruction == current and state.timer_deadline == timer
    assert repo.load(state.incident_id).knowledge_answers[-1].citations == reply.citations
    assert coach.last_route == ("safety", "controls", "gate", "answer")


def test_wrong_policy_jurisdiction_date_and_demo_optout_exclude_sources(scene):
    coach, state, _ = scene
    for context in (
        KnowledgeContext(policy_id="wrong", jurisdiction="wrong", reference_date=date(2026,9,8), allow_synthetic=True),
        KnowledgeContext(policy_id="demo-meridian", jurisdiction="DEMO", reference_date=date(2030,1,1), allow_synthetic=True),
        KnowledgeContext(policy_id="demo-meridian", jurisdiction="DEMO", reference_date=date(2026,9,8)),
    ):
        coach.handle_event(state, ContextEvent(context=context))
        assert not coach.turn(state, "/ask What is my excess?").citations
        assert not coach.turn(state, "Do I need to call police?").citations


def test_injury_question_preempts_lookup(scene):
    coach, state, _ = scene
    assert coach.turn(state, "/ask My chest hurts; what does my policy say?").terminate
    assert not state.knowledge_answers
    assert state.status is SessionStatus.STOOD_DOWN


def test_fault_and_claim_recommendations_are_refused(scene):
    coach, state, _ = scene
    coach.turn(state, "/knowledge-demo")
    for question in ("Whose fault is it?", "Should I claim?"):
        assert not coach.turn(state, question).citations
        assert state.knowledge_answers[-1].status == "refused"


def test_invalid_corpus_degrades_without_blocking_safety(tmp_path, monkeypatch):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "bad.json").write_text("not json")
    monkeypatch.setenv("CRISIS_COACH_KNOWLEDGE_DIR", str(sources))
    coach = CollisionWorkflow(executor=build_capture_executor(tmp_path / "attachments"))
    state, _ = coach.start()
    for answer in ("No", "No", "Yes", "/knowledge-demo"): coach.turn(state, answer)
    assert "could not be loaded" in coach.turn(state, "/ask What is my excess?").text
    assert coach.turn(state, "My chest hurts").terminate


def test_citation_tampering_and_unreviewed_sources_are_rejected():
    passage = SourcePassage(source_id="p", title="Policy", section="1", source_uri="local:policy", corpus="policy", policy_id="p", effective_from=date(2026,1,1), topics=("excess",), text="Excess: 500", reviewed=True)
    query = KnowledgeQuery(question="Excess?", corpus="policy", topic="excess", context=KnowledgeContext(policy_id="p", reference_date=date(2026,9,8)))
    retriever = LocalKnowledgeRetriever(SourceCorpus(passages=(passage,)))
    answer = retriever.retrieve(query)
    changed = answer.model_copy(update={"citations": (passage.model_copy(update={"text":"Excess: 0"}),)})
    with pytest.raises(ValueError): validate_grounding(changed, query, (passage,))
    unreviewed = passage.model_copy(update={"reviewed":False})
    assert not LocalKnowledgeRetriever(SourceCorpus(passages=(unreviewed,))).retrieve(query).citations


def test_unknown_topics_and_question_interrupt_do_not_collect(scene):
    coach, state, _ = scene
    before = state.current_evidence_id
    coach.turn(state, "/ask Will the insurer pay for a rental car?")
    assert state.current_evidence_id == before
    assert state.knowledge_answers[-1].status == "not_found"


def test_multiple_passages_are_shown_without_silent_conflict_resolution():
    base = dict(title="Policy", section="1", source_uri="local:p", corpus="policy", policy_id="p", effective_from=date(2026,1,1), topics=("excess",), reviewed=True)
    passages = (SourcePassage(source_id="a", text="Excess 500", **base), SourcePassage(source_id="b", text="Excess 600", **base))
    query = KnowledgeQuery(question="Excess?", corpus="policy", topic="excess", context=KnowledgeContext(policy_id="p", reference_date=date(2026,9,8)))
    answer = LocalKnowledgeRetriever(SourceCorpus(passages=passages)).retrieve(query)
    assert len(answer.citations) == 2
    assert "not a determination" in answer.message


def test_unknown_citation_cannot_be_marked_found():
    with pytest.raises(ValidationError): KnowledgeAnswer(question="q", status="found", message="unsupported")


def test_langgraph_cited_question_and_export(tmp_path, monkeypatch):
    pytest.importorskip("langgraph")
    pytest.importorskip("docx")
    monkeypatch.delenv("CRISIS_COACH_KNOWLEDGE_DIR", raising=False)
    coach = CollisionWorkflow(backend="langgraph", executor=build_capture_executor(tmp_path / "attachments"))
    state, _ = coach.start()
    for text in ("No", "No", "Yes", "/knowledge-demo"):
        coach.turn(state, text)
    reply = coach.turn(state, "/ask What is my excess?")
    assert reply.citations and coach.last_route == ("safety", "controls", "gate", "answer")
    coach.turn(state, "/export")
    from docx import Document
    doc = Document(tmp_path / "exports" / state.exports[-1].relative_path)
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "SYNTHETIC DEMO" in text and "demo-meridian-excess" in text
