import api from '@/lib/api';

// -- Types --

export type RubricLevel = {
  id: number;
  label: string;
  points: number;
  description: string;
  orderIndex: number;
};

export type RubricCriterion = {
  id: number;
  title: string;
  description: string;
  orderIndex: number;
  weight: number;
  levels: RubricLevel[];
};

export type Rubric = {
  id: number;
  title: string;
  description: string;
  status: string;
  createdBy: number;
  createdAt: string;
  updatedAt: string;
  criteria: RubricCriterion[];
};

export type LevelInput = {
  label: string;
  points: number;
  description?: string;
  orderIndex?: number;
};

export type CriterionInput = {
  title: string;
  description?: string;
  orderIndex?: number;
  weight?: number;
  levels?: LevelInput[];
};

export type RubricInput = {
  title: string;
  description?: string;
  criteria?: CriterionInput[];
};

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

// -- API Functions --

/** GET /rubrics/ — Fetch all rubrics (paginated, returns results array). */
export async function listRubrics(): Promise<Rubric[]> {
  const response = await api.get<Paginated<Rubric>>('/rubrics/');
  return response.data.results;
}

/** GET /rubrics/:id — Fetch a single rubric by ID, including criteria and levels. */
export async function getRubric(id: number): Promise<Rubric> {
  const response = await api.get<Rubric>(`/rubrics/${id}`);
  return response.data;
}

/** POST /rubrics/ — Create a new rubric with criteria and levels. */
export async function createRubric(payload: RubricInput): Promise<Rubric> {
  const response = await api.post<Rubric>('/rubrics/', payload);
  return response.data;
}

/** PATCH /rubrics/:id — Partially update an existing rubric. */
export async function updateRubric(id: number, payload: RubricInput): Promise<Rubric> {
  const response = await api.patch<Rubric>(`/rubrics/${id}`, payload);
  return response.data;
}

/** DELETE /rubrics/:id — Permanently delete a rubric. */
export async function deleteRubric(id: number): Promise<void> {
  await api.delete(`/rubrics/${id}`);
}

/** POST /rubrics/:id/archive — Soft-archive a rubric. */
export async function archiveRubric(id: number): Promise<Rubric> {
  const response = await api.post<Rubric>(`/rubrics/${id}/archive`);
  return response.data;
}
