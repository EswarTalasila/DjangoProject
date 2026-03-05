import api from '@/lib/api';

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export type DashboardCourse = {
  courseId?: number;
  courseName?: string;
  enrolledCount: number;
  activeEnrollments: number;
  assignmentCount: number;
  avgCompletionRate: number | null;
  avgScore: number | null;
  pendingGrades: number;
};

export type DashboardDTO = {
  generatedAt: string;
  courses: DashboardCourse[];
};

export type CourseSummaryAssignment = {
  assignmentId?: number;
  assessmentTitle?: string;
  assessmentCategory: string | null;
  submittedCount: number;
  totalStudents: number;
  completionPct: number | null;
  gradedCount: number;
  avgScore: number | null;
  pendingGrades: number;
};

export type CourseSummaryDTO = {
  generatedAt: string;
  filters: {
    startDate: string | null;
    endDate: string | null;
    category: string | null;
    assessmentId: number | null;
  };
  courseId?: number;
  courseName?: string;
  enrolledCount: number;
  assignments: CourseSummaryAssignment[];
};

export type DistributionBin = {
  range: string;
  count: number;
};

export type AssignmentSummaryDTO = {
  generatedAt: string;
  filters: { startDate: string | null; endDate: string | null };
  assignmentId?: number;
  assessmentTitle?: string;
  assessmentCategory: string | null;
  totalStudents: number;
  submittedCount: number;
  gradedCount: number;
  completionPct: number | null;
  avgScore: number | null;
  medianScore: number | null;
  highScore: number | null;
  lowScore: number | null;
  distribution: DistributionBin[];
};

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** GET /visualizations/dashboard — Fetch the teacher dashboard overview with per-course stats. */
export async function fetchDashboard(): Promise<DashboardDTO> {
  const { data } = await api.get('/visualizations/dashboard');
  return data;
}

/** GET /visualizations/courses/:id/summary — Fetch per-assignment completion and score stats for a course. */
export async function fetchCourseSummary(
  courseId: number,
  params?: { startDate?: string; endDate?: string; category?: string; assessmentId?: number },
): Promise<CourseSummaryDTO> {
  const { data } = await api.get(`/visualizations/courses/${courseId}/summary`, { params });
  return data;
}

/** GET /visualizations/assignments/:id/summary — Fetch detailed stats and score distribution for an assignment. */
export async function fetchAssignmentSummary(
  assignmentId: number,
  params?: { startDate?: string; endDate?: string },
): Promise<AssignmentSummaryDTO> {
  const { data } = await api.get(`/visualizations/assignments/${assignmentId}/summary`, {
    params,
  });
  return data;
}

