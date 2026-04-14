'use client';

import type {
  QuestionGroupInput,
  QuestionInput,
  SubmissionMode,
} from '@/lib/assignment-template-api';

export type BuilderGradingMode = 'AUTO' | 'MANUAL' | 'HYBRID';

export type StudioValidationPanel = 'header' | 'structure' | 'editor' | 'settings';
export type StudioValidationSection =
  | 'title'
  | 'questionList'
  | 'prompt'
  | 'responseConfig'
  | 'rubricBinding'
  | 'groupManager';

export type StudioValidationIssue = {
  id: string;
  level: 'error';
  panel: StudioValidationPanel;
  section: StudioValidationSection;
  title: string;
  detail: string;
  questionIndex?: number;
  groupClientKey?: string;
};

type BuildValidationIssuesArgs = {
  title: string;
  questions: QuestionInput[];
  questionGroups: QuestionGroupInput[];
  gradingMode: BuilderGradingMode;
  submissionMode: SubmissionMode;
  assignmentTemplateRubricId: number | null;
  effectiveRubricId: (question: QuestionInput) => number | null;
};

export function buildStudioValidationIssues({
  title,
  questions,
  questionGroups,
  gradingMode,
  submissionMode,
  assignmentTemplateRubricId,
  effectiveRubricId,
}: BuildValidationIssuesArgs): StudioValidationIssue[] {
  const issues: StudioValidationIssue[] = [];
  const hasSpecificRubrics =
    questionGroups.some((group) => group.rubricId != null) ||
    questions.some((question) => question.rubricId != null);

  if (!title.trim()) {
    issues.push({
      id: 'assignment-template-title',
      level: 'error',
      panel: 'header',
      section: 'title',
      title: 'Assignment Template Title',
      detail: 'Title is required before saving.',
    });
  }

  if (questions.length === 0 && submissionMode !== 'UPLOAD_ONLY') {
    issues.push({
      id: 'question-list-empty',
      level: 'error',
      panel: 'structure',
      section: 'questionList',
      title: 'Question List',
      detail: 'Add at least one question to continue.',
    });
  }

  for (const group of questionGroups) {
    if (!group.name.trim()) {
      issues.push({
        id: `group-name-${group.clientKey}`,
        level: 'error',
        panel: 'settings',
        section: 'groupManager',
        groupClientKey: group.clientKey,
        title: 'Question Group',
        detail: 'Group name cannot be blank.',
      });
    }
  }

  if (gradingMode === 'AUTO' && assignmentTemplateRubricId != null) {
    issues.push({
      id: 'assignment-template-rubric-auto',
      level: 'error',
      panel: 'settings',
      section: 'rubricBinding',
      title: 'Assignment Template Rubric',
      detail: 'AUTO mode does not allow rubric linkage.',
    });
  }

  if (assignmentTemplateRubricId != null && hasSpecificRubrics) {
    issues.push({
      id: 'assignment-template-rubric-mixed-specific-rubrics',
      level: 'error',
      panel: 'settings',
      section: 'rubricBinding',
      title: 'Rubric Configuration',
      detail:
        'Use either an assignment template rubric or question/group rubrics. Clear one before using the other.',
    });
  }

  for (const group of questionGroups) {
    if (gradingMode === 'AUTO' && group.rubricId != null) {
      issues.push({
        id: `group-rubric-auto-${group.clientKey}`,
        level: 'error',
        panel: 'settings',
        section: 'groupManager',
        groupClientKey: group.clientKey,
        title: `Group: ${group.name || 'Unnamed group'}`,
        detail: 'AUTO mode does not allow group rubrics.',
      });
    }
  }

  for (let index = 0; index < questions.length; index += 1) {
    const question = questions[index];
    if (!question.prompt.trim()) {
      issues.push({
        id: `question-${index}-prompt`,
        level: 'error',
        panel: 'editor',
        section: 'prompt',
        questionIndex: index,
        title: `Question ${index + 1}`,
        detail: 'Question prompt is required.',
      });
      continue;
    }

    if (question.type === 'MULTIPLE_CHOICE') {
      const choices = question.data?.choices ?? [];
      if (choices.length < 2) {
        issues.push({
          id: `question-${index}-choices-count`,
          level: 'error',
          panel: 'editor',
          section: 'responseConfig',
          questionIndex: index,
          title: `Question ${index + 1}`,
          detail: 'Multiple choice questions require at least two answer choices.',
        });
      } else if (choices.some((choice) => !choice.prompt.trim())) {
        issues.push({
          id: `question-${index}-choices-empty`,
          level: 'error',
          panel: 'editor',
          section: 'responseConfig',
          questionIndex: index,
          title: `Question ${index + 1}`,
          detail: 'Every answer choice requires prompt text.',
        });
      }
    }

    if (question.type === 'NUMBER_SCALE') {
      const min = question.data?.min ?? 0;
      const max = question.data?.max ?? 0;
      if (min >= max) {
        issues.push({
          id: `question-${index}-number-scale-range`,
          level: 'error',
          panel: 'editor',
          section: 'responseConfig',
          questionIndex: index,
          title: `Question ${index + 1}`,
          detail: 'Scale minimum must be less than the maximum.',
        });
      }
      const target = question.data?.target;
      if (target != null && (target < min || target > max)) {
        issues.push({
          id: `question-${index}-number-scale-target`,
          level: 'error',
          panel: 'editor',
          section: 'responseConfig',
          questionIndex: index,
          title: `Question ${index + 1}`,
          detail: 'Scale target must fall within the configured range.',
        });
      }
    }

    const hasRubric = effectiveRubricId(question) != null;
    const hasDirectRubric = question.rubricId != null;
    const strategy = question.gradingStrategy ?? 'AUTO';

    if (gradingMode === 'AUTO' && hasDirectRubric) {
      issues.push({
        id: `question-${index}-rubric-auto`,
        level: 'error',
        panel: 'settings',
        section: 'rubricBinding',
        questionIndex: index,
        title: `Question ${index + 1}`,
        detail: 'AUTO mode does not allow question-level rubrics.',
      });
    }

    if (gradingMode === 'MANUAL' && !hasRubric) {
      issues.push({
        id: `question-${index}-rubric-manual`,
        level: 'error',
        panel: 'settings',
        section: 'rubricBinding',
        questionIndex: index,
        title: `Question ${index + 1}`,
        detail: 'MANUAL mode requires a rubric at the question, group, or assignment template level.',
      });
    }

    if (gradingMode === 'HYBRID' && strategy === 'MANUAL' && !hasRubric) {
      issues.push({
        id: `question-${index}-rubric-hybrid-manual`,
        level: 'error',
        panel: 'settings',
        section: 'rubricBinding',
        questionIndex: index,
        title: `Question ${index + 1}`,
        detail: 'Questions using MANUAL grading require a rubric.',
      });
    }

    if (gradingMode === 'HYBRID' && strategy === 'AUTO' && hasRubric) {
      issues.push({
        id: `question-${index}-rubric-hybrid-auto`,
        level: 'error',
        panel: 'settings',
        section: 'rubricBinding',
        questionIndex: index,
        title: `Question ${index + 1}`,
        detail: 'Questions using AUTO grading cannot have a rubric attached.',
      });
    }
  }

  return issues;
}
