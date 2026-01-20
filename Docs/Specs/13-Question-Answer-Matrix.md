# Question and Answer Type Matrix

## Purpose
Define the supported question types, answer payloads, and grading behavior for parity with the current system.

## Matrix
| QuestionType | AnswerType | Required Fields | Auto-Scorable | Grading Logic |
|---|---|---|---|---|
| MULTIPLE_CHOICE | MultipleChoiceAnswer | selected: int[] | Yes | Exact match vs correct answers, score sum | 
| SHORT_ANSWER | ShortAnswerAnswer | text: string | Partial | Case sensitivity + trim flags | 
| NUMBER_SCALE | NumberScaleAnswer | value: number | Yes | Direct mapping or range score | 
| MOOD_METER | MoodMeterAnswer | x: int, y: int | No | No scoring | 
| GRADING_CRITERIA | RubricAnswer | levelId: int | No | Teacher selects rubric level | 

## Data constraints
- Question definitions are immutable once submissions exist (version or lock).
- Answers must reference stable question identifiers.
- Validation rules must match frontend expectations.

## Sources
- `Migration Notes/dev_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-entities.wsd`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-dto.wsd`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
