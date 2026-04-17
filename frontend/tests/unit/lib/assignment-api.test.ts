import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "../mocks/server";

const API_BASE = "http://localhost/_test/api/v1";

async function loadAssignmentApi() {
  vi.resetModules();
  process.env.NEXT_PUBLIC_API_URL = API_BASE;
  return import("@/lib/assignment-api");
}

const sampleAssignment = {
  id: 1,
  title: "HW 1",
  assignmentTemplateId: 10,
  assignmentTemplateTitle: "Math Quiz",
  audienceType: "COURSE",
  courseId: 5,
  targetTeacherId: null,
  openAt: "2026-01-01T00:00:00Z",
  dueAt: "2026-02-01T00:00:00Z",
  status: "ACTIVE",
};

const sampleAssignmentContent = {
  id: 10,
  title: "Math Quiz",
  assignmentId: 1,
  assignmentTemplateId: 10,
  assignmentTemplateTitle: "Math Quiz",
  category: "Quiz",
  gradingMode: "HYBRID",
  scoringPolicy: "STANDARD",
  submissionMode: "DIGITAL",
  rubricId: 50,
  questionGroups: [],
  teacherCriteria: [],
  questions: [],
};

describe("assignment api", () => {
  describe("createAssignment", () => {
    it("creates and returns a new assignment", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/`, async ({ request }) => {
          const body = (await request.json()) as { assignmentTemplateId?: number };
          return HttpResponse.json(
            { ...sampleAssignment, assignmentTemplateId: body.assignmentTemplateId },
            { status: 201 },
          );
        }),
      );

      const { createAssignment } = await loadAssignmentApi();
      const result = await createAssignment({
        title: "Unit Test Assignment",
        assignmentTemplateId: 10,
        audienceType: "COURSE",
        courseId: 5,
        openAt: "2026-01-01T00:00:00Z",
      });

      expect(result.id).toBe(1);
      expect(result.assignmentTemplateId).toBe(10);
    });
  });

  describe("getAssignment", () => {
    it("fetches a single assignment by ID", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1`, () =>
          HttpResponse.json(sampleAssignment),
        ),
      );

      const { getAssignment } = await loadAssignmentApi();
      const result = await getAssignment(1);

      expect(result.id).toBe(1);
      expect(result.title).toBe("HW 1");
    });

    it("propagates 404 error", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/999`, () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 }),
        ),
      );

      const { getAssignment } = await loadAssignmentApi();
      await expect(getAssignment(999)).rejects.toThrow();
    });
  });

  describe("updateAssignment", () => {
    it("patches and returns the updated assignment", async () => {
      server.use(
        http.patch(`${API_BASE}/assignments/1`, async ({ request }) => {
          const body = (await request.json()) as { title?: string };
          return HttpResponse.json({ ...sampleAssignment, title: body.title });
        }),
      );

      const { updateAssignment } = await loadAssignmentApi();
      const result = await updateAssignment(1, { title: "HW 1 Updated" });

      expect(result.title).toBe("HW 1 Updated");
    });
  });

  describe("getAssignmentContent", () => {
    it("fetches the effective assignment content snapshot", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1/template`, () =>
          HttpResponse.json(sampleAssignmentContent),
        ),
      );

      const { getAssignmentContent } = await loadAssignmentApi();
      const result = await getAssignmentContent(1);

      expect(result.assignmentId).toBe(1);
      expect(result.assignmentTemplateTitle).toBe("Math Quiz");
    });
  });

  describe("assignment extension helpers", () => {
    it("posts a teacher-authored assignment question", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/questions`, async ({ request }) => {
          const body = (await request.json()) as { prompt?: string };
          return HttpResponse.json(
            {
              ...sampleAssignmentContent,
              questions: [
                {
                  questionId: 111,
                  id: 111,
                  type: "SHORT_ANSWER",
                  prompt: body.prompt,
                  maxPoints: 5,
                  autoGradable: false,
                  graded: false,
                  image: null,
                  data: {},
                  selectAll: null,
                  min: null,
                  max: null,
                  groupId: null,
                  rubricId: null,
                  gradingStrategy: "MANUAL",
                  orderIndex: 0,
                  origin: "TEACHER_ADDITION",
                  lockedFromSource: false,
                  sourceQuestionId: null,
                },
              ],
            },
            { status: 201 },
          );
        }),
      );

      const { addAssignmentQuestion } = await loadAssignmentApi();
      const result = await addAssignmentQuestion(1, {
        type: "SHORT_ANSWER",
        prompt: "Teacher follow-up",
        maxPoints: 5,
      });

      expect(result.questions[0].prompt).toBe("Teacher follow-up");
      expect(result.questions[0].origin).toBe("TEACHER_ADDITION");
    });

    it("updates and deletes a teacher-authored assignment question", async () => {
      server.use(
        http.patch(`${API_BASE}/assignments/1/questions/111`, async ({ request }) => {
          const body = (await request.json()) as { prompt?: string; maxPoints?: number };
          return HttpResponse.json({
            ...sampleAssignmentContent,
            questions: [
              {
                questionId: 111,
                id: 111,
                type: "SHORT_ANSWER",
                prompt: body.prompt,
                maxPoints: body.maxPoints,
                autoGradable: false,
                graded: false,
                image: null,
                data: {},
                selectAll: null,
                min: null,
                max: null,
                groupId: null,
                rubricId: null,
                gradingStrategy: "MANUAL",
                orderIndex: 0,
                origin: "TEACHER_ADDITION",
                lockedFromSource: false,
                sourceQuestionId: null,
              },
            ],
          });
        }),
        http.delete(`${API_BASE}/assignments/1/questions/111`, () =>
          HttpResponse.json({ ...sampleAssignmentContent, questions: [] }),
        ),
      );

      const { updateAssignmentQuestion, deleteAssignmentQuestion } = await loadAssignmentApi();
      const updated = await updateAssignmentQuestion(1, 111, {
        type: "SHORT_ANSWER",
        prompt: "Teacher revised",
        maxPoints: 6,
      });
      expect(updated.questions[0].prompt).toBe("Teacher revised");
      expect(updated.questions[0].maxPoints).toBe(6);

      const deleted = await deleteAssignmentQuestion(1, 111);
      expect(deleted.questions).toEqual([]);
    });

    it("posts a teacher-authored rubric criterion", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/teacher-criteria`, async ({ request }) => {
          const body = (await request.json()) as { title?: string; weight?: number };
          return HttpResponse.json(
            {
              ...sampleAssignmentContent,
              teacherCriteria: [
                {
                  id: 801,
                  title: body.title,
                  description: "",
                  weight: body.weight,
                  orderIndex: 0,
                  levels: [],
                },
              ],
            },
            { status: 201 },
          );
        }),
      );

      const { addAssignmentTeacherCriterion } = await loadAssignmentApi();
      const result = await addAssignmentTeacherCriterion(1, {
        title: "Local rigor",
        weight: 2,
      });

      expect(result.teacherCriteria[0].title).toBe("Local rigor");
      expect(result.teacherCriteria[0].weight).toBe(2);
    });

    it("updates and deletes teacher-authored rubric criteria and levels", async () => {
      server.use(
        http.patch(`${API_BASE}/assignments/1/teacher-criteria/801`, async ({ request }) => {
          const body = (await request.json()) as { title?: string; description?: string; weight?: number };
          return HttpResponse.json({
            ...sampleAssignmentContent,
            teacherCriteria: [
              {
                id: 801,
                title: body.title,
                description: body.description,
                weight: body.weight,
                orderIndex: 0,
                levels: [
                  {
                    id: 901,
                    label: "Meets",
                    points: 2,
                    description: "",
                    orderIndex: 0,
                  },
                ],
              },
            ],
          });
        }),
        http.patch(
          `${API_BASE}/assignments/1/teacher-criteria/801/levels/901`,
          async ({ request }) => {
            const body = (await request.json()) as { label?: string; description?: string; points?: number };
            return HttpResponse.json({
              ...sampleAssignmentContent,
              teacherCriteria: [
                {
                  id: 801,
                  title: "Local rigor",
                  description: "",
                  weight: 2,
                  orderIndex: 0,
                  levels: [
                    {
                      id: 901,
                      label: body.label,
                      points: body.points,
                      description: body.description,
                      orderIndex: 0,
                    },
                  ],
                },
              ],
            });
          },
        ),
        http.delete(`${API_BASE}/assignments/1/teacher-criteria/801`, () =>
          HttpResponse.json({ ...sampleAssignmentContent, teacherCriteria: [] }),
        ),
        http.delete(`${API_BASE}/assignments/1/teacher-criteria/801/levels/901`, () =>
          HttpResponse.json({
            ...sampleAssignmentContent,
            teacherCriteria: [
              {
                id: 801,
                title: "Local rigor",
                description: "",
                weight: 2,
                orderIndex: 0,
                levels: [],
              },
            ],
          }),
        ),
      );

      const {
        updateAssignmentTeacherCriterion,
        updateAssignmentTeacherCriterionLevel,
        deleteAssignmentTeacherCriterion,
        deleteAssignmentTeacherCriterionLevel,
      } = await loadAssignmentApi();

      const updatedCriterion = await updateAssignmentTeacherCriterion(1, 801, {
        title: "Local rigor revised",
        description: "Updated",
        weight: 3,
      });
      expect(updatedCriterion.teacherCriteria[0].title).toBe("Local rigor revised");

      const updatedLevel = await updateAssignmentTeacherCriterionLevel(1, 801, 901, {
        label: "Exceeds",
        description: "Updated level",
        points: 4,
      });
      expect(updatedLevel.teacherCriteria[0].levels[0].label).toBe("Exceeds");

      const deletedLevel = await deleteAssignmentTeacherCriterionLevel(1, 801, 901);
      expect(deletedLevel.teacherCriteria[0].levels).toEqual([]);

      const deletedCriterion = await deleteAssignmentTeacherCriterion(1, 801);
      expect(deletedCriterion.teacherCriteria).toEqual([]);
    });

    it("reorders teacher-authored assignment questions", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/questions/reorder`, async ({ request }) => {
          const body = (await request.json()) as { orderedIds?: number[] };
          return HttpResponse.json({
            ...sampleAssignmentContent,
            questions: body.orderedIds?.map((id, index) => ({
              questionId: id,
              id,
              type: "SHORT_ANSWER",
              prompt: `Teacher ${index + 1}`,
              maxPoints: 1,
              autoGradable: false,
              graded: false,
              image: null,
              data: {},
              selectAll: null,
              min: null,
              max: null,
              groupId: null,
              rubricId: null,
              gradingStrategy: "MANUAL",
              orderIndex: index + 1,
              origin: "TEACHER_ADDITION",
              lockedFromSource: false,
              sourceQuestionId: null,
            })),
          });
        }),
      );

      const { reorderAssignmentQuestions } = await loadAssignmentApi();
      const result = await reorderAssignmentQuestions(1, [103, 102]);

      expect(result.questions.map((question) => question.id)).toEqual([103, 102]);
    });

    it("adds levels and reorders teacher-authored rubric criteria", async () => {
      server.use(
        http.post(
          `${API_BASE}/assignments/1/teacher-criteria/801/levels`,
          async ({ request }) => {
            const body = (await request.json()) as { label?: string; points?: number };
            return HttpResponse.json(
              {
                ...sampleAssignmentContent,
                teacherCriteria: [
                  {
                    id: 801,
                    title: "Local rigor",
                    description: "",
                    weight: 2,
                    orderIndex: 0,
                    levels: [
                      {
                        id: 901,
                        label: body.label,
                        points: body.points,
                        description: "",
                        orderIndex: 0,
                      },
                    ],
                  },
                ],
              },
              { status: 201 },
            );
          },
        ),
        http.post(`${API_BASE}/assignments/1/teacher-criteria/reorder`, async ({ request }) => {
          const body = (await request.json()) as { orderedIds?: number[] };
          return HttpResponse.json({
            ...sampleAssignmentContent,
            teacherCriteria: body.orderedIds?.map((id, index) => ({
              id,
              title: `Criterion ${id}`,
              description: "",
              weight: 1,
              orderIndex: index,
              levels: [],
            })),
          });
        }),
        http.post(
          `${API_BASE}/assignments/1/teacher-criteria/801/levels/reorder`,
          async ({ request }) => {
            const body = (await request.json()) as { orderedIds?: number[] };
            return HttpResponse.json({
              ...sampleAssignmentContent,
              teacherCriteria: [
                {
                  id: 801,
                  title: "Local rigor",
                  description: "",
                  weight: 2,
                  orderIndex: 0,
                  levels: body.orderedIds?.map((id, index) => ({
                    id,
                    label: `Level ${id}`,
                    points: index,
                    description: "",
                    orderIndex: index,
                  })),
                },
              ],
            });
          },
        ),
      );

      const {
        addAssignmentTeacherCriterionLevel,
        reorderAssignmentTeacherCriteria,
        reorderAssignmentTeacherCriterionLevels,
      } = await loadAssignmentApi();

      const leveled = await addAssignmentTeacherCriterionLevel(1, 801, {
        label: "Exceeds",
        points: 4,
      });
      expect(leveled.teacherCriteria[0].levels[0].label).toBe("Exceeds");

      const reordered = await reorderAssignmentTeacherCriteria(1, [802, 801]);
      expect(reordered.teacherCriteria.map((criterion) => criterion.id)).toEqual([802, 801]);

      const reorderedLevels = await reorderAssignmentTeacherCriterionLevels(1, 801, [902, 901]);
      expect(reorderedLevels.teacherCriteria[0].levels.map((level) => level.id)).toEqual([902, 901]);
    });

    it("lists reusable assignment question images", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1/images`, () =>
          HttpResponse.json([
            {
              id: "img-1",
              storageKey: "questions/img-1.png",
              url: "/api/v1/assignments/images/questions/img-1.png",
              originalFilename: "img-1.png",
              mimeType: "image/png",
              sizeBytes: 1234,
            },
          ]),
        ),
      );

      const { listReusableAssignmentImages } = await loadAssignmentApi();
      const result = await listReusableAssignmentImages(1);

      expect(result).toHaveLength(1);
      expect(result[0].id).toBe("img-1");
    });
  });

  describe("purgeAssignment", () => {
    it("purges an archived assignment without error", async () => {
      server.use(
        http.delete(`${API_BASE}/assignments/1`, ({ request }) => {
          expect(new URL(request.url).searchParams.get("purge")).toBe("true");
          return new HttpResponse(null, { status: 204 });
        }),
      );

      const { purgeAssignment } = await loadAssignmentApi();
      await expect(purgeAssignment(1)).resolves.toBeUndefined();
    });
  });

  describe("archiveAssignment", () => {
    it("archives and returns the assignment", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/archive`, () =>
          HttpResponse.json({ ...sampleAssignment, status: "ARCHIVED" }),
        ),
      );

      const { archiveAssignment } = await loadAssignmentApi();
      const result = await archiveAssignment(1);

      expect(result.status).toBe("ARCHIVED");
    });
  });

  describe("restoreAssignment", () => {
    it("restores and returns the assignment", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/restore`, () =>
          HttpResponse.json({ ...sampleAssignment, status: "ACTIVE" }),
        ),
      );

      const { restoreAssignment } = await loadAssignmentApi();
      const result = await restoreAssignment(1);

      expect(result.status).toBe("ACTIVE");
    });
  });

  describe("archive bundle helpers", () => {
    it("fetches archive bundle metadata", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1/archive-bundle`, () =>
          HttpResponse.json({
            id: 7,
            assignmentId: 1,
            identifiable: true,
            filename: "bundle.zip",
            sizeBytes: 1234,
            sha256Hash: "abc",
            generatedAt: "2026-01-01T00:00:00Z",
            generatedByUserId: 3,
            manifest: {},
          }),
        ),
      );

      const { getAssignmentArchiveBundle } = await loadAssignmentApi();
      const result = await getAssignmentArchiveBundle(1);

      expect(result.filename).toBe("bundle.zip");
      expect(result.assignmentId).toBe(1);
    });

    it("generates archive bundle metadata", async () => {
      server.use(
        http.post(`${API_BASE}/assignments/1/archive-bundle`, () =>
          HttpResponse.json(
            {
              id: 7,
              assignmentId: 1,
              identifiable: true,
              filename: "bundle.zip",
              sizeBytes: 1234,
              sha256Hash: "abc",
              generatedAt: "2026-01-01T00:00:00Z",
              generatedByUserId: 3,
              manifest: {},
            },
            { status: 201 },
          ),
        ),
      );

      const { generateAssignmentArchiveBundle } = await loadAssignmentApi();
      const result = await generateAssignmentArchiveBundle(1);

      expect(result.filename).toBe("bundle.zip");
    });

    it("downloads archive bundle zip data", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/1/archive-bundle/download`, () =>
          new HttpResponse(new Blob(["zipdata"]), {
            status: 200,
            headers: { "content-disposition": 'attachment; filename="archive.zip"' },
          }),
        ),
      );

      const { downloadAssignmentArchiveBundle } = await loadAssignmentApi();
      const result = await downloadAssignmentArchiveBundle(1);

      expect(result.filename).toBe("archive.zip");
      expect(result.blob).toBeInstanceOf(Blob);
    });
  });

  describe("listAssignmentsByCourse", () => {
    it("handles paginated response", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/courses/5`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssignment],
          }),
        ),
      );

      const { listAssignmentsByCourse } = await loadAssignmentApi();
      const result = await listAssignmentsByCourse(5);

      expect(result).toHaveLength(1);
      expect(result[0].courseId).toBe(5);
    });

    it("handles flat array response", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/courses/5`, () =>
          HttpResponse.json([sampleAssignment]),
        ),
      );

      const { listAssignmentsByCourse } = await loadAssignmentApi();
      const result = await listAssignmentsByCourse(5);

      expect(result).toHaveLength(1);
    });

    it("passes includeArchived=true when requested", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/courses/5`, ({ request }) => {
          expect(new URL(request.url).searchParams.get("includeArchived")).toBe("true");
          return HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssignment],
          });
        }),
      );

      const { listAssignmentsByCourse } = await loadAssignmentApi();
      const result = await listAssignmentsByCourse(5, { includeArchived: true });

      expect(result).toHaveLength(1);
    });
  });

  describe("listAssignmentsForUser", () => {
    it("handles paginated response with numeric user ID", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/users/42`, () =>
          HttpResponse.json({
            count: 1,
            next: null,
            previous: null,
            results: [sampleAssignment],
          }),
        ),
      );

      const { listAssignmentsForUser } = await loadAssignmentApi();
      const result = await listAssignmentsForUser(42);

      expect(result).toHaveLength(1);
    });

    it("handles flat array response with string user ID", async () => {
      server.use(
        http.get(`${API_BASE}/assignments/users/me`, () =>
          HttpResponse.json([sampleAssignment]),
        ),
      );

      const { listAssignmentsForUser } = await loadAssignmentApi();
      const result = await listAssignmentsForUser("me");

      expect(result).toHaveLength(1);
    });
  });
});
