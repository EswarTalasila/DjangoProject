import api from '@/lib/api';

export type CourseSummary = {
  id: number;
  name: string;
  studentCount: number;
  assignmentIds: number[];
};

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export async function listCourses(): Promise<CourseSummary[]> {
  const response = await api.get<Paginated<CourseSummary> | CourseSummary[]>('/courses/');
  const data = response.data;
  if (Array.isArray(data)) return data;
  return data.results ?? [];
}

export async function createCourse(name: string): Promise<CourseSummary> {
  const response = await api.post<CourseSummary>('/courses/', { name });
  return response.data;
}
