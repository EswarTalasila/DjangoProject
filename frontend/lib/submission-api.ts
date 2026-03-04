import api from '@/lib/api';

// -- Types --

export type SubmissionStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'GRADED';

export type AnswerPayload = {
  questionId: number;
  type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE';
  data: { selected?: number[]; text?: string; val?: number | null };
  score?: number | null;
};

export type SubmissionDTO = {
  id: number;
  assignmentId: number;
  studentId: number | null;
  teacherId: number | null;
  submittedAt: string | null;
  score: number | null;
  status: SubmissionStatus;
  answers: AnswerPayload[];
};

export type SubmissionCompactDTO = {
  id: number;
  assignmentId: number;
  submittedAt: string | null;
  score: number | null;
  status: SubmissionStatus;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

// -- API calls --

export async function getStudentSubmission(
  studentId: number,
  assignmentId: number,
): Promise<SubmissionDTO> {
  const { data } = await api.get(
    `/students/${studentId}/assignments/${assignmentId}/submission/`,
  );
  return data;
}

export async function saveDraft(
  studentId: number,
  assignmentId: number,
  answers: AnswerPayload[],
): Promise<SubmissionDTO> {
  const { data } = await api.patch(
    `/students/${studentId}/assignments/${assignmentId}/draft/`,
    { answers },
  );
  return data;
}

export async function submitFinal(
  assignmentId: number,
  studentId: number,
  answers: AnswerPayload[],
): Promise<SubmissionDTO> {
  const { data } = await api.post(
    `/assignments/${assignmentId}/submissions`,
    {
      assignmentId,
      studentId,
      status: 'SUBMITTED',
      answers,
    },
  );
  return data;
}

export async function getSubmission(submissionId: number): Promise<SubmissionDTO> {
  const { data } = await api.get(`/submissions/${submissionId}`);
  return data;
}

export async function listMySubmissions(
  status?: SubmissionStatus,
): Promise<Paginated<SubmissionCompactDTO> | SubmissionCompactDTO[]> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  const qs = params.toString();
  const { data } = await api.get(`/submissions/me${qs ? `?${qs}` : ''}`);
  return data;
}

export async function listAssignmentSubmissions(
  assignmentId: number,
): Promise<Paginated<SubmissionCompactDTO> | SubmissionCompactDTO[]> {
  const { data } = await api.get(`/assignments/${assignmentId}/submissions`);
  return data;
}

export async function listStudentSubmissions(
  studentId: number,
): Promise<Paginated<SubmissionCompactDTO> | SubmissionCompactDTO[]> {
  const { data } = await api.get(`/students/${studentId}/submissions/`);
  return data;
}

export async function overrideSubmissionScore(
  submissionId: number,
  scores: number[],
): Promise<SubmissionDTO> {
  const { data } = await api.patch(`/submissions/${submissionId}/override-score`, scores);
  return data;
}
