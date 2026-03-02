import api from '@/lib/api';

// -- Types --

export type GradingMode = 'AUTO' | 'MANUAL' | 'HYBRID' | 'RUBRIC' | 'REFLECTION' | 'MOOD_METER';
export type QuestionKind = 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE' | 'MOOD_METER';

export type McqChoice = {
  prompt: string;
  score: number;
};

export type QuestionData = {
  choices?: McqChoice[];
  selectAll?: boolean;
  caseSensitive?: boolean;
  trim?: boolean;
  min?: number;
  max?: number;
  target?: number | null;
  labels?: string[];
};

export type Question = {
  questionId: number;
  id: number;
  type: QuestionKind;
  prompt: string;
  maxPoints: number;
  autoGradable: boolean;
  graded: boolean;
  data: QuestionData | null;
  selectAll: boolean | null;
  min: number | null;
  max: number | null;
};

export type Assessment = {
  id: number;
  title: string;
  category: string | null;
  gradingMode: GradingMode;
  questions: Question[];
  rubricId: number | null;
  rubricAssessmentIds: number[];
};

export type QuestionInput = {
  type: QuestionKind;
  prompt: string;
  maxPoints: number;
  data?: QuestionData;
};

export type AssessmentInput = {
  title: string;
  category?: string | null;
  gradingMode: GradingMode;
  questions: QuestionInput[];
  rubricId?: number | null;
  rubricAssessmentIds?: number[];
};

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

// -- API Functions --

export async function listAssessments(): Promise<Assessment[]> {
  const response = await api.get<Paginated<Assessment>>('/assessments/');
  return response.data.results;
}

export async function getAssessment(id: number): Promise<Assessment> {
  const response = await api.get<Assessment>(`/assessments/${id}`);
  return response.data;
}

export async function createAssessment(payload: AssessmentInput): Promise<Assessment> {
  const response = await api.post<Assessment>('/assessments/', payload);
  return response.data;
}

export async function updateAssessment(id: number, payload: AssessmentInput): Promise<Assessment> {
  const response = await api.patch<Assessment>(`/assessments/${id}`, payload);
  return response.data;
}

export async function deleteAssessment(id: number): Promise<void> {
  await api.delete(`/assessments/${id}`);
}
