import json
import os
import time
from typing import Type, TypeVar

import streamlit as st
from openai import APIConnectionError, APIError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from models import (
    Assessment,
    RefinedPack,
    ReviewResult,
    StudyContent,
    StudyPlan,
    WorkflowState,
)

T = TypeVar("T", bound=BaseModel)

MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
MAX_REFINEMENTS = 2


def get_api_key() -> str:
    """Read the API key from Streamlit secrets first, then environment variables."""
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to Streamlit Secrets before deploying."
        )
    return key


def get_client() -> OpenAI:
    return OpenAI(api_key=get_api_key())


def call_ai(system_prompt: str, user_prompt: str, schema: Type[T]) -> T:
    """Call the AI model, enforce JSON output, validate it, and retry on failures."""
    client = get_client()
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            raw = response.choices[0].message.content
            if not raw:
                raise ValueError("The model returned empty output.")

            data = json.loads(raw)
            return schema.model_validate(data)

        except (APIConnectionError, RateLimitError, APIError) as error:
            last_error = error
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            last_error = error

        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)

    raise RuntimeError(
        f"AI stage failed after {MAX_RETRIES} attempts: {last_error}"
    )


def run_planning(state: WorkflowState) -> WorkflowState:
    student = state.student

    prompt = f"""
Create a personalized study plan for this student.

Student profile:
{student.model_dump_json(indent=2)}

Requirements:
- Create a clear title.
- Create 3 to 6 measurable learning objectives.
- List the key concepts that should be covered.
- Build a realistic schedule that fits the student's available study time.
- Set an appropriate difficulty level.

Return ONLY valid JSON with this structure:
{{
  "title": "string",
  "objectives": ["string"],
  "concepts": ["string"],
  "schedule": ["string"],
  "difficulty": "string"
}}
"""

    state.plan = call_ai(
        "You are an expert instructional designer who creates practical study plans.",
        prompt,
        StudyPlan,
    )
    return state


def run_content_generation(state: WorkflowState) -> WorkflowState:
    prompt = f"""
Create personalized study content using the student's profile and study plan.

Student profile:
{state.student.model_dump_json(indent=2)}

Study plan:
{state.plan.model_dump_json(indent=2)}

Requirements:
- Write a concise summary.
- List important key concepts.
- Write clear detailed notes.
- Include useful examples.
- Include common misconceptions or mistakes.
- Match the requested academic level, language, goals, and learning style.

Return ONLY valid JSON with this structure:
{{
  "summary": "string",
  "key_concepts": ["string"],
  "detailed_notes": "string",
  "examples": ["string"],
  "misconceptions": ["string"]
}}
"""

    state.content = call_ai(
        "You are an expert educational content creator. Be accurate, clear, and pedagogically useful.",
        prompt,
        StudyContent,
    )
    return state


def run_assessment(state: WorkflowState) -> WorkflowState:
    prompt = f"""
Create a 10-question practice assessment based on the study content below.

Student level:
{state.student.level}

Study content:
{state.content.model_dump_json(indent=2)}

Requirements:
- Create exactly 10 questions.
- Mix easy, medium, and hard questions.
- You may use short-answer and multiple-choice questions.
- If a question has options, the correct answer must exactly match one option.
- Every question must include a correct answer and a short explanation.
- Include an answer_key list that matches the 10 questions in order.

Return ONLY valid JSON with this structure:
{{
  "questions": [
    {{
      "question": "string",
      "options": ["string"] or null,
      "answer": "string",
      "explanation": "string",
      "difficulty": "easy" | "medium" | "hard"
    }}
  ],
  "answer_key": ["string"]
}}
"""

    state.assessment = call_ai(
        "You are an expert assessment designer who writes fair and educational practice questions.",
        prompt,
        Assessment,
    )
    return state


def run_review(state: WorkflowState) -> WorkflowState:
    prompt = f"""
Review this personalized study pack as a strict educational quality reviewer.

Study plan:
{state.plan.model_dump_json(indent=2)}

Study content:
{state.content.model_dump_json(indent=2)}

Assessment:
{state.assessment.model_dump_json(indent=2)}

Check:
1. Coverage of the learning objectives.
2. Clarity and usefulness of the notes.
3. Internal factual consistency.
4. Appropriate difficulty for the student.
5. Whether questions can be answered from the study material.
6. Whether question answers and explanations are consistent.
7. Whether the pack is personalized to the student profile.

Set passed=true only if the pack is strong enough to use without important corrections.

Return ONLY valid JSON with this structure:
{{
  "passed": true,
  "score": 0,
  "issues": ["string"],
  "suggestions": ["string"]
}}
"""

    state.review = call_ai(
        "You are a strict educational quality-control reviewer. Identify real issues rather than giving automatic approval.",
        prompt,
        ReviewResult,
    )
    return state


def run_refinement(state: WorkflowState) -> WorkflowState:
    prompt = f"""
Improve the study content and assessment using the quality review feedback.

Student profile:
{state.student.model_dump_json(indent=2)}

Study plan:
{state.plan.model_dump_json(indent=2)}

Current content:
{state.content.model_dump_json(indent=2)}

Current assessment:
{state.assessment.model_dump_json(indent=2)}

Review feedback:
{state.review.model_dump_json(indent=2)}

Requirements:
- Fix every meaningful issue reported by the reviewer.
- Preserve accurate material that does not need changes.
- Keep the pack personalized to the student's level, goals, language, and learning style.
- Ensure answers and explanations are consistent.

Return ONLY valid JSON with this structure:
{{
  "content": {{
    "summary": "string",
    "key_concepts": ["string"],
    "detailed_notes": "string",
    "examples": ["string"],
    "misconceptions": ["string"]
  }},
  "assessment": {{
    "questions": [
      {{
        "question": "string",
        "options": ["string"] or null,
        "answer": "string",
        "explanation": "string",
        "difficulty": "easy" | "medium" | "hard"
      }}
    ],
    "answer_key": ["string"]
  }}
}}
"""

    refined = call_ai(
        "You are an expert educational editor who fixes quality issues precisely.",
        prompt,
        RefinedPack,
    )

    state.content = refined.content
    state.assessment = refined.assessment
    state.refinement_count += 1
    return state


def validate_assessment(assessment: Assessment) -> list[str]:
    errors: list[str] = []

    if len(assessment.questions) != 10:
        errors.append("Assessment must contain exactly 10 questions.")

    if len(assessment.answer_key) != len(assessment.questions):
        errors.append("Answer key length does not match the number of questions.")

    for index, question in enumerate(assessment.questions, start=1):
        if not question.question.strip():
            errors.append(f"Question {index} is empty.")
        if not question.answer.strip():
            errors.append(f"Question {index} has no answer.")
        if not question.explanation.strip():
            errors.append(f"Question {index} has no explanation.")
        if question.options and question.answer not in question.options:
            errors.append(
                f"Question {index}: the correct answer is not present in the options."
            )

    return errors


def validate_pack(state: WorkflowState) -> None:
    if state.plan is None:
        raise ValueError("Missing study plan.")
    if state.content is None:
        raise ValueError("Missing study content.")
    if state.assessment is None:
        raise ValueError("Missing assessment.")
    if state.review is None:
        raise ValueError("Missing quality review.")
    if not state.content.key_concepts:
        raise ValueError("No key concepts were generated.")

    assessment_errors = validate_assessment(state.assessment)
    if assessment_errors:
        raise ValueError(" ".join(assessment_errors))


def run_workflow(student, progress_callback=None) -> WorkflowState:
    state = WorkflowState(student=student)

    try:
        if progress_callback:
            progress_callback("Planning", "Creating learning objectives and study structure...")
        state = run_planning(state)

        if progress_callback:
            progress_callback("Content Generation", "Generating personalized notes and examples...")
        state = run_content_generation(state)

        if progress_callback:
            progress_callback("Assessment", "Creating practice questions and explanations...")
        state = run_assessment(state)

        if progress_callback:
            progress_callback("Review", "Checking coverage, quality, and consistency...")
        state = run_review(state)

        while (
            not state.review.passed
            and state.refinement_count < MAX_REFINEMENTS
        ):
            if progress_callback:
                progress_callback(
                    "Refinement",
                    f"Improving the pack from review feedback (attempt {state.refinement_count + 1}/{MAX_REFINEMENTS})...",
                )
            state = run_refinement(state)

            if progress_callback:
                progress_callback("Review", "Reviewing the refined study pack...")
            state = run_review(state)

        validate_pack(state)

        state.final_pack = {
            "student": state.student.model_dump(),
            "plan": state.plan.model_dump(),
            "content": state.content.model_dump(),
            "assessment": state.assessment.model_dump(),
            "review": state.review.model_dump(),
            "refinement_count": state.refinement_count,
        }

    except Exception as error:
        state.errors.append(str(error))

    return state
