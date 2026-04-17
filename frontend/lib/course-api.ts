import api from "@/lib/api";

export interface CourseSummary {
  id: number;
  name: string;
  studentCount: number;
  assignmentIds: number[];
  teacherId: number | null;
  teacherName: string | null;
  createdAt: string | null;
  status: 'ACTIVE' | 'ARCHIVED';
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

/** GET /courses/ — List courses visible to the current user. */
export async function listCourses(
  options?: { includeArchived?: boolean },
): Promise<CourseSummary[]> {
  const params = options?.includeArchived ? { includeArchived: true } : undefined;
  const response = await api.get<Paginated<CourseSummary> | CourseSummary[]>(
    "/courses/",
    { params },
  );
  const data = response.data;
  if (Array.isArray(data)) return data;
  return data.results;
}

/** POST /courses/ — Create a new course with the given name. */
export async function createCourse(name: string): Promise<CourseSummary> {
  const response = await api.post<CourseSummary>("/courses/", { name });
  return response.data;
}

/** GET /courses/:id — Fetch a single course by ID. */
export async function getCourse(courseId: number): Promise<CourseSummary> {
  const response = await api.get<CourseSummary>(`/courses/${courseId}`);
  return response.data;
}

/** PATCH /courses/:id — Rename a course. */
export async function updateCourse(
  courseId: number,
  name: string
): Promise<CourseSummary> {
  const response = await api.patch<CourseSummary>(`/courses/${courseId}`, {
    name,
  });
  return response.data;
}

/** DELETE /courses/:id?purge=true — Permanently purge an archived course. */
export async function purgeCourse(courseId: number): Promise<void> {
  await api.delete(`/courses/${courseId}?purge=true`);
}

/** GET /courses/:id/students — List all students enrolled in a course. */
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

/** POST /courses/:id/students — Enroll a new student in a course (creates account if needed). */
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

/** DELETE /courses/:id/students/:uid — Remove a student from a course. */
export async function removeStudentFromCourse(
  courseId: number,
  studentUserId: number
): Promise<void> {
  await api.delete(`/courses/${courseId}/students/${studentUserId}`);
}

/** POST /courses/:id/archive — Soft-archive a course. */
export async function archiveCourse(courseId: number): Promise<CourseSummary> {
  const response = await api.post<CourseSummary>(`/courses/${courseId}/archive`, {});
  return response.data;
}

/** POST /courses/:id/restore — Restore a previously archived course. */
export async function restoreCourse(courseId: number): Promise<CourseSummary> {
  const response = await api.post<CourseSummary>(`/courses/${courseId}/restore`, {});
  return response.data;
}
