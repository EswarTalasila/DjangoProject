export interface QuestionBase {
  id?: string;
  type: 'multiple-choice' | 'short-answer' | 'scale';
  prompt: string;
  maxPoints: number;
  image?: File | string | null;
  graded?: boolean;
  autoGradable: boolean;
}

export interface Choice {
    prompt: string;
    score: number;
}

export interface MultipleChoiceQuestion extends QuestionBase {
  type: 'multiple-choice';
  choices: Choice[];
  selectAll: boolean;
  correctAnswers: number[];
}

export interface ShortAnswerQuestion extends QuestionBase {
  type: 'short-answer';
  caseSensitive?: boolean;
  trim?: boolean;
}

export interface ScaleQuestion extends QuestionBase {
  type: 'scale';
  min: number;
  max: number;
  target?: number;
}
