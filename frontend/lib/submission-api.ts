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
  userId: number,
  status?: SubmissionStatus,
): Promise<{ results: SubmissionCompactDTO[] }> {
  const params = new URLSearchParams({ userId: String(userId) });
  if (status) params.set('status', status);
  const { data } = await api.get(`/submissions/mine?${params}`);
  return data;
}

export async function listAssignmentSubmissions(
  assignmentId: number,
): Promise<{ results: SubmissionDTO[] }> {
  const { data } = await api.get(`/assignments/${assignmentId}/submissions`);
  return data;
}
