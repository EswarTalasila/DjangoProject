import api from "@/lib/api";

export interface CourseSummary {
  id: number;
  name: string;
  studentCount: number;
  assignmentIds: number[];
  teacherId: number | null;
  teacherName: string | null;
  createdAt: string | null;
}

export interface CourseStudent {
  id: number;
  name: string;
  username: string;
  role: string;
  consent: boolean;
  courseId: number;
  enrolledAt: string | null;
}

interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function listCourses(): Promise<CourseSummary[]> {
  const response = await api.get<Paginated<CourseSummary> | CourseSummary[]>(
    "/courses/"
  );
  const data = response.data;
  if (Array.isArray(data)) return data;
  return data.results;
}

export async function createCourse(name: string): Promise<CourseSummary> {
  const response = await api.post<CourseSummary>("/courses/", { name });
  return response.data;
}

export async function getCourse(courseId: number): Promise<CourseSummary> {
  const response = await api.get<CourseSummary>(`/courses/${courseId}`);
  return response.data;
}

export async function updateCourse(
  courseId: number,
  name: string
): Promise<CourseSummary> {
  const response = await api.patch<CourseSummary>(`/courses/${courseId}`, {
    name,
  });
  return response.data;
}

export async function deleteCourse(courseId: number): Promise<void> {
  await api.delete(`/courses/${courseId}`);
}

export async function listStudentsInCourse(
  courseId: number
): Promise<CourseStudent[]> {
  const response = await api.get<Paginated<CourseStudent> | CourseStudent[]>(
    `/courses/${courseId}/students`
  );
  const data = response.data;
  if (Array.isArray(data)) return data;
  return data.results;
}

export async function addStudentToCourse(
  courseId: number,
  payload: { name: string; consent?: boolean; password?: string }
): Promise<CourseStudent> {
  const response = await api.post<CourseStudent>(
    `/courses/${courseId}/students`,
    payload
  );
  return response.data;
}

export async function removeStudentFromCourse(
  courseId: number,
  studentUserId: number
): Promise<void> {
  await api.delete(`/courses/${courseId}/students/${studentUserId}`);
}
