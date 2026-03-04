import api from '@/lib/api';
import type { CourseSummary } from '@/lib/course-api';
import type { Assessment } from '@/lib/assessment-api';
import type { Assignment } from '@/lib/assignment-api';

// -- Lifecycle state type --

export type LifecycleStatus = 'ACTIVE' | 'ARCHIVED';

// -- Course lifecycle --

export async function archiveCourse(courseId: number): Promise<CourseSummary> {
  const { data } = await api.post<CourseSummary>(`/courses/${courseId}/archive`, {});
  return data;
}

export async function restoreCourse(courseId: number): Promise<CourseSummary> {
  const { data } = await api.post<CourseSummary>(`/courses/${courseId}/restore`, {});
  return data;
}

export async function purgeCourse(courseId: number): Promise<void> {
  await api.delete(`/courses/${courseId}`);
}

// -- Assessment lifecycle --

export async function archiveAssessment(assessmentId: number): Promise<Assessment> {
  const { data } = await api.post<Assessment>(`/assessments/${assessmentId}/archive`, {});
  return data;
}

export async function restoreAssessment(assessmentId: number): Promise<Assessment> {
  const { data } = await api.post<Assessment>(`/assessments/${assessmentId}/restore`, {});
  return data;
}

export async function purgeAssessment(assessmentId: number): Promise<void> {
  await api.delete(`/assessments/${assessmentId}`);
}

// -- Assignment lifecycle --

export async function archiveAssignment(assignmentId: number): Promise<Assignment> {
  const { data } = await api.post<Assignment>(`/assignments/${assignmentId}/archive`, {});
  return data;
}

export async function restoreAssignment(assignmentId: number): Promise<Assignment> {
  const { data } = await api.post<Assignment>(`/assignments/${assignmentId}/restore`, {});
  return data;
}

export async function purgeAssignment(assignmentId: number): Promise<void> {
  await api.delete(`/assignments/${assignmentId}`);
}
