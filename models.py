from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    subject: str
    topic: str
    level: str
    goals: str
    study_time: int = Field(gt=0, le=480)
    learning_style: str
    language: str


class StudyPlan(BaseModel):
    title: str
    objectives: List[str]
    concepts: List[str]
    schedule: List[str]
    difficulty: str


class StudyContent(BaseModel):
    summary: str
    key_concepts: List[str]
    detailed_notes: str
    examples: List[str]
    misconceptions: List[str]


class Question(BaseModel):
    question: str
    options: Optional[List[str]] = None
    answer: str
    explanation: str
    difficulty: Literal["easy", "medium", "hard"]


class Assessment(BaseModel):
    questions: List[Question]
    answer_key: List[str]


class ReviewResult(BaseModel):
    passed: bool
    score: float = Field(ge=0, le=100)
    issues: List[str]
    suggestions: List[str]


class RefinedPack(BaseModel):
    content: StudyContent
    assessment: Assessment


class WorkflowState(BaseModel):
    student: StudentProfile
    plan: Optional[StudyPlan] = None
    content: Optional[StudyContent] = None
    assessment: Optional[Assessment] = None
    review: Optional[ReviewResult] = None
    final_pack: Optional[dict] = None
    errors: List[str] = Field(default_factory=list)
    refinement_count: int = 0
