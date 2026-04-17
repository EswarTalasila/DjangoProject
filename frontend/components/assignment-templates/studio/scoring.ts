'use client';

import type { QuestionData, QuestionInput } from '@/lib/assignment-template-api';

function positiveChoiceScores(data: QuestionData | undefined): number[] {
  return (data?.choices ?? [])
    .map((choice) => Number(choice.score) || 0)
    .filter((score) => score > 0);
}

export function deriveMcqMaxPoints(data: QuestionData | undefined): number {
  const scores = positiveChoiceScores(data);
  if (scores.length === 0) return 0;

  if (data?.selectAll) {
    return scores.reduce((sum, score) => sum + score, 0);
  }

  return Math.max(...scores);
}

export function syncDerivedQuestionPoints(question: QuestionInput): QuestionInput {
  if (question.type !== 'MULTIPLE_CHOICE') {
    return question;
  }

  const derived = deriveMcqMaxPoints(question.data);
  if (question.maxPoints === derived) {
    return question;
  }

  return {
    ...question,
    maxPoints: derived,
  };
}
