import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AssignmentComposerPanel from '@/components/assignments/AssignmentComposerPanel';

const {
  mockAddAssignmentQuestion,
  mockAddAssignmentTeacherCriterion,
  mockAddAssignmentTeacherCriterionLevel,
  mockDeleteAssignmentQuestion,
  mockDeleteAssignmentTeacherCriterion,
  mockDeleteAssignmentTeacherCriterionLevel,
  mockListReusableAssignmentImages,
  mockReorderAssignmentQuestions,
  mockReorderAssignmentTeacherCriteria,
  mockReorderAssignmentTeacherCriterionLevels,
  mockUploadAssignmentQuestionImage,
  mockReuseAssignmentQuestionImage,
  mockDeleteAssignmentQuestionImage,
  mockUpdateAssignmentQuestion,
  mockUpdateAssignmentTeacherCriterion,
  mockUpdateAssignmentTeacherCriterionLevel,
  mockGetRubric,
  mockToastSuccess,
  mockToastError,
} = vi.hoisted(() => ({
  mockAddAssignmentQuestion: vi.fn(),
  mockAddAssignmentTeacherCriterion: vi.fn(),
  mockAddAssignmentTeacherCriterionLevel: vi.fn(),
  mockDeleteAssignmentQuestion: vi.fn(),
  mockDeleteAssignmentTeacherCriterion: vi.fn(),
  mockDeleteAssignmentTeacherCriterionLevel: vi.fn(),
  mockListReusableAssignmentImages: vi.fn(),
  mockReorderAssignmentQuestions: vi.fn(),
  mockReorderAssignmentTeacherCriteria: vi.fn(),
  mockReorderAssignmentTeacherCriterionLevels: vi.fn(),
  mockUploadAssignmentQuestionImage: vi.fn(),
  mockReuseAssignmentQuestionImage: vi.fn(),
  mockDeleteAssignmentQuestionImage: vi.fn(),
  mockUpdateAssignmentQuestion: vi.fn(),
  mockUpdateAssignmentTeacherCriterion: vi.fn(),
  mockUpdateAssignmentTeacherCriterionLevel: vi.fn(),
  mockGetRubric: vi.fn(),
  mockToastSuccess: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: { success: mockToastSuccess, error: mockToastError },
}));

vi.mock('@/lib/assignment-api', () => ({
  addAssignmentQuestion: mockAddAssignmentQuestion,
  addAssignmentTeacherCriterion: mockAddAssignmentTeacherCriterion,
  addAssignmentTeacherCriterionLevel: mockAddAssignmentTeacherCriterionLevel,
  deleteAssignmentQuestion: mockDeleteAssignmentQuestion,
  deleteAssignmentTeacherCriterion: mockDeleteAssignmentTeacherCriterion,
  deleteAssignmentTeacherCriterionLevel: mockDeleteAssignmentTeacherCriterionLevel,
  listReusableAssignmentImages: mockListReusableAssignmentImages,
  reorderAssignmentQuestions: mockReorderAssignmentQuestions,
  reorderAssignmentTeacherCriteria: mockReorderAssignmentTeacherCriteria,
  reorderAssignmentTeacherCriterionLevels: mockReorderAssignmentTeacherCriterionLevels,
  reuseAssignmentQuestionImage: mockReuseAssignmentQuestionImage,
  uploadAssignmentQuestionImage: mockUploadAssignmentQuestionImage,
  deleteAssignmentQuestionImage: mockDeleteAssignmentQuestionImage,
  updateAssignmentQuestion: mockUpdateAssignmentQuestion,
  updateAssignmentTeacherCriterion: mockUpdateAssignmentTeacherCriterion,
  updateAssignmentTeacherCriterionLevel: mockUpdateAssignmentTeacherCriterionLevel,
}));

vi.mock('@/lib/rubric-api', () => ({
  getRubric: mockGetRubric,
}));

vi.mock('@/components/media/ImagePicker', () => ({
  default: ({
    onBrowse,
    onUpload,
    onSelect,
    onRemove,
  }: {
    onBrowse?: () => Promise<unknown[]>;
    onUpload?: (file: File) => Promise<unknown>;
    onSelect: (image: unknown) => Promise<void> | void;
    onRemove: () => Promise<void> | void;
  }) => (
    <div data-testid="mock-image-picker">
      <button
        type="button"
        onClick={async () => {
          const images = (await onBrowse?.()) ?? [];
          if (images[0]) {
            await onSelect(images[0]);
          }
        }}
      >
        reuse-image
      </button>
      <button
        type="button"
        onClick={async () => {
          if (!onUpload) return;
          await onUpload(new File(['demo'], 'demo.png', { type: 'image/png' }));
        }}
      >
        upload-image
      </button>
      <button type="button" onClick={() => void onRemove()}>
        remove-image
      </button>
    </div>
  ),
}));

function makeContent(overrides: Record<string, unknown> = {}) {
  return {
    id: 10,
    title: 'Assignment Template Alpha',
    assignmentId: 1,
    assignmentTemplateId: 10,
    assignmentTemplateTitle: 'Assignment Template Alpha',
    category: 'Exit Ticket',
    gradingMode: 'HYBRID',
    scoringPolicy: 'STANDARD',
    submissionMode: 'DIGITAL',
    rubricId: 51,
    questionGroups: [{ id: 1, name: 'Group A', rubricId: null, orderIndex: 0 }],
    teacherCriteria: [],
    questions: [
      {
        questionId: 101,
        id: 101,
        type: 'SHORT_ANSWER',
        prompt: 'Researcher prompt',
        maxPoints: 5,
        autoGradable: false,
        graded: false,
        image: null,
        data: { trim: true, caseSensitive: false },
        selectAll: null,
        min: null,
        max: null,
        groupId: 1,
        rubricId: null,
        gradingStrategy: 'MANUAL',
        orderIndex: 0,
        origin: 'TEMPLATE',
        lockedFromSource: true,
        sourceQuestionId: 201,
      },
      {
        questionId: 102,
        id: 102,
        type: 'SHORT_ANSWER',
        prompt: 'Teacher prompt',
        maxPoints: 2,
        autoGradable: false,
        graded: false,
        image: null,
        data: { trim: true, caseSensitive: false },
        selectAll: null,
        min: null,
        max: null,
        groupId: null,
        rubricId: null,
        gradingStrategy: 'MANUAL',
        orderIndex: 1,
        origin: 'TEACHER_ADDITION',
        lockedFromSource: false,
        sourceQuestionId: null,
      },
    ],
    ...overrides,
  };
}

function renderComposer(overrides: Record<string, unknown> = {}) {
  const onContentChange = vi.fn();

  render(
    <AssignmentComposerPanel
      assignmentId={1}
      content={makeContent(overrides)}
      canCompose={true}
      onContentChange={onContentChange}
    />,
  );

  return { onContentChange };
}

describe('AssignmentComposerPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockGetRubric.mockResolvedValue({
      id: 51,
      title: 'Locked Research Rubric',
      description: 'Researcher-defined rubric context.',
      status: 'ACTIVE',
      createdBy: 1,
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
      criteria: [
        {
          id: 900,
          title: 'Evidence quality',
          description: 'Use source-backed reasoning.',
          orderIndex: 0,
          weight: 3,
          levels: [],
        },
      ],
    });
  });

  it('renders the builder with locked researcher content and editable teacher content', async () => {
    renderComposer();

    expect(screen.getByText('Question structure')).toBeInTheDocument();
    expect(screen.getByText('Assignment rubric')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /shared rubric/i }));
    expect(await screen.findByText('Locked Research Rubric')).toBeInTheDocument();
    expect(screen.getAllByText('Evidence quality')).toHaveLength(2);

    await userEvent.click(
      screen.getByRole('button', {
        name: /teacher prompt/i,
      }),
    );

    expect(screen.getByText('Editable question')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Teacher prompt')).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole('button', {
        name: /researcher prompt/i,
      }),
    );

    expect(screen.getByText('Locked template question')).toBeInTheDocument();
    expect(screen.getAllByText('Shared template').length).toBeGreaterThan(0);
    expect(
      screen.queryByRole('button', { name: /remove researcher prompt/i }),
    ).not.toBeInTheDocument();
  });

  it('adds a teacher-authored question from the builder rail', async () => {
    const nextContent = makeContent({
      questions: [
        ...makeContent().questions,
        {
          questionId: 103,
          id: 103,
          type: 'NUMBER_SCALE',
          prompt: 'Teacher follow-up',
          maxPoints: 4,
          autoGradable: true,
          graded: false,
          image: null,
          data: { min: 1, max: 5, target: null },
          selectAll: null,
          min: 1,
          max: 5,
          groupId: null,
          rubricId: null,
          gradingStrategy: 'AUTO',
          orderIndex: 2,
          origin: 'TEACHER_ADDITION',
          lockedFromSource: false,
          sourceQuestionId: null,
        },
      ],
    });
    mockAddAssignmentQuestion.mockResolvedValue(nextContent);
    const user = userEvent.setup();
    const { onContentChange } = renderComposer();

    await user.click(screen.getByRole('button', { name: /add local question/i }));
    await user.clear(screen.getByLabelText('Prompt'));
    await user.type(screen.getByLabelText('Prompt'), 'Teacher follow-up');
    await user.clear(screen.getByLabelText('Points'));
    await user.type(screen.getByLabelText('Points'), '4');
    await user.click(screen.getByRole('button', { name: /^add question$/i }));

    await waitFor(() =>
      expect(mockAddAssignmentQuestion).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          type: 'SHORT_ANSWER',
          prompt: 'Teacher follow-up',
          maxPoints: 4,
          data: { trim: true, caseSensitive: false },
        }),
      ),
    );
    expect(onContentChange).toHaveBeenCalledWith(nextContent);
  });

  it('updates teacher-added multiple-choice questions including option edits', async () => {
    const content = makeContent({
      questions: [
        makeContent().questions[0],
        {
          ...makeContent().questions[1],
          type: 'MULTIPLE_CHOICE',
          data: {
            choices: [
              { prompt: 'Alpha', score: 0 },
              { prompt: 'Beta', score: 1 },
            ],
            selectAll: true,
          },
          selectAll: true,
        },
      ],
    });
    mockUpdateAssignmentQuestion.mockResolvedValue(content);
    const user = userEvent.setup();

    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={content}
        canCompose={true}
        onContentChange={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: /teacher prompt/i }));
    const choiceInputs = screen.getAllByPlaceholderText('Choice text');
    await user.clear(choiceInputs[0]);
    await user.type(choiceInputs[0], 'Gamma');
    await user.clear(screen.getByLabelText('Prompt', { selector: '#edit-question-prompt-102' }));
    await user.type(
      screen.getByLabelText('Prompt', { selector: '#edit-question-prompt-102' }),
      'Teacher prompt revised',
    );
    await user.click(screen.getByRole('button', { name: /save question/i }));

    await waitFor(() =>
      expect(mockUpdateAssignmentQuestion).toHaveBeenCalledWith(
        1,
        102,
        expect.objectContaining({
          prompt: 'Teacher prompt revised',
          data: {
            choices: [
              { prompt: 'Gamma', score: 0 },
              { prompt: 'Beta', score: 1 },
            ],
            selectAll: true,
          },
        }),
      ),
    );
  });

  it('reorders and deletes teacher-added questions without exposing researcher edits', async () => {
    const content = makeContent({
      questions: [
        makeContent().questions[0],
        makeContent().questions[1],
        {
          ...makeContent().questions[1],
          id: 103,
          questionId: 103,
          prompt: 'Teacher second',
          orderIndex: 2,
        },
      ],
    });
    const reorderedContent = makeContent({
      questions: [
        makeContent().questions[0],
        {
          ...makeContent().questions[1],
          id: 103,
          questionId: 103,
          prompt: 'Teacher second',
          orderIndex: 1,
        },
        {
          ...makeContent().questions[1],
          orderIndex: 2,
        },
      ],
    });
    const deletedContent = makeContent({
      questions: [makeContent().questions[0]],
    });
    mockReorderAssignmentQuestions.mockResolvedValue(reorderedContent);
    mockDeleteAssignmentQuestion.mockResolvedValue(deletedContent);
    const user = userEvent.setup();
    const onContentChange = vi.fn();

    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={content}
        canCompose={true}
        onContentChange={onContentChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: /teacher second/i }));
    await user.click(screen.getByRole('button', { name: /move teacher second earlier/i }));

    await waitFor(() =>
      expect(mockReorderAssignmentQuestions).toHaveBeenCalledWith(1, [103, 102]),
    );

    await user.click(screen.getByRole('button', { name: /teacher prompt/i }));
    await user.click(screen.getByRole('button', { name: /remove teacher prompt/i }));

    await waitFor(() => expect(mockDeleteAssignmentQuestion).toHaveBeenCalledWith(1, 102));
    expect(onContentChange).toHaveBeenNthCalledWith(1, reorderedContent);
    expect(onContentChange).toHaveBeenNthCalledWith(2, deletedContent);
  });

  it('adds, updates, and reorders teacher-authored rubric criteria and levels', async () => {
    const addedCriterionContent = makeContent({
      teacherCriteria: [
        {
          id: 701,
          title: 'Local rigor',
          description: 'Check for local classroom expectations.',
          weight: 2,
          orderIndex: 0,
          levels: [],
        },
      ],
    });
    const addedLevelContent = makeContent({
      ...addedCriterionContent,
      teacherCriteria: [
        {
          ...addedCriterionContent.teacherCriteria[0],
          levels: [
            {
              id: 901,
              label: 'Exceeds',
              description: 'Strong evidence',
              points: 4,
              orderIndex: 0,
            },
          ],
        },
      ],
    });
    const reorderedContent = makeContent({
      teacherCriteria: [
        {
          id: 702,
          title: 'Second criterion',
          description: '',
          weight: 1,
          orderIndex: 0,
          levels: [],
        },
        {
          id: 701,
          title: 'Local rigor',
          description: 'Check for local classroom expectations.',
          weight: 2,
          orderIndex: 1,
          levels: [],
        },
      ],
    });
    mockAddAssignmentTeacherCriterion.mockResolvedValue(addedCriterionContent);
    mockAddAssignmentTeacherCriterionLevel.mockResolvedValue(addedLevelContent);
    mockReorderAssignmentTeacherCriteria.mockResolvedValue(reorderedContent);
    const user = userEvent.setup();
    const onContentChange = vi.fn();

    const view = render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={makeContent({
          teacherCriteria: [
            {
              id: 702,
              title: 'Second criterion',
              description: '',
              weight: 1,
              orderIndex: 1,
              levels: [],
            },
          ],
        })}
        canCompose={true}
        onContentChange={onContentChange}
      />,
    );

    await user.type(screen.getByLabelText('Criterion title'), 'Local rigor');
    await user.type(
      screen.getByLabelText('Description', { selector: '#assignment-criterion-description' }),
      'Check for local classroom expectations.',
    );
    await user.clear(screen.getByLabelText('Weight', { selector: '#assignment-criterion-weight' }));
    await user.type(screen.getByLabelText('Weight', { selector: '#assignment-criterion-weight' }), '2');
    await user.click(screen.getByRole('button', { name: /add criterion/i }));

    await waitFor(() =>
      expect(mockAddAssignmentTeacherCriterion).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          title: 'Local rigor',
          description: 'Check for local classroom expectations.',
          weight: 2,
        }),
      ),
    );

    view.rerender(
      <AssignmentComposerPanel
        assignmentId={1}
        content={addedCriterionContent}
        canCompose={true}
        onContentChange={onContentChange}
      />,
    );

    await user.type(
      screen.getByLabelText('Level label', { selector: '#criterion-level-label-701' }),
      'Exceeds',
    );
    await user.clear(screen.getByLabelText('Points', { selector: '#criterion-level-points-701' }));
    await user.type(
      screen.getByLabelText('Points', { selector: '#criterion-level-points-701' }),
      '4',
    );
    await user.type(
      screen.getByLabelText('Description', { selector: '#criterion-level-description-701' }),
      'Strong evidence',
    );
    await user.click(screen.getAllByRole('button', { name: /add level/i })[0]);

    await waitFor(() =>
      expect(mockAddAssignmentTeacherCriterionLevel).toHaveBeenCalledWith(
        1,
        701,
        expect.objectContaining({
          label: 'Exceeds',
          description: 'Strong evidence',
          points: 4,
        }),
      ),
    );

    view.rerender(
      <AssignmentComposerPanel
        assignmentId={1}
        content={makeContent({
          teacherCriteria: [
            {
              id: 701,
              title: 'Local rigor',
              description: 'Check for local classroom expectations.',
              weight: 2,
              orderIndex: 0,
              levels: [],
            },
            {
              id: 702,
              title: 'Second criterion',
              description: '',
              weight: 1,
              orderIndex: 1,
              levels: [],
            },
          ],
        })}
        canCompose={true}
        onContentChange={onContentChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: /move second criterion earlier/i }));

    await waitFor(() =>
      expect(mockReorderAssignmentTeacherCriteria).toHaveBeenCalledWith(1, [702, 701]),
    );
    expect(onContentChange).toHaveBeenCalledWith(addedCriterionContent);
    expect(onContentChange).toHaveBeenCalledWith(addedLevelContent);
    expect(onContentChange).toHaveBeenCalledWith(reorderedContent);
  });

  it('updates and deletes teacher-authored criteria and levels', async () => {
    const content = makeContent({
      teacherCriteria: [
        {
          id: 701,
          title: 'Local rigor',
          description: 'Check for local classroom expectations.',
          weight: 2,
          orderIndex: 0,
          levels: [
            {
              id: 901,
              label: 'Exceeds',
              description: 'Strong evidence',
              points: 4,
              orderIndex: 0,
            },
          ],
        },
      ],
    });
    const updatedCriterionContent = makeContent({
      ...content,
      teacherCriteria: [
        {
          ...content.teacherCriteria[0],
          title: 'Local rigor revised',
          description: 'Updated criterion',
          weight: 3,
        },
      ],
    });
    const updatedLevelContent = makeContent({
      ...updatedCriterionContent,
      teacherCriteria: [
        {
          ...updatedCriterionContent.teacherCriteria[0],
          levels: [
            {
              id: 901,
              label: 'Outstanding',
              description: 'Updated level',
              points: 5,
              orderIndex: 0,
            },
          ],
        },
      ],
    });
    const deletedLevelContent = makeContent({
      ...updatedCriterionContent,
      teacherCriteria: [
        {
          ...updatedCriterionContent.teacherCriteria[0],
          levels: [],
        },
      ],
    });
    const deletedCriterionContent = makeContent({ teacherCriteria: [] });

    mockUpdateAssignmentTeacherCriterion.mockResolvedValue(updatedCriterionContent);
    mockUpdateAssignmentTeacherCriterionLevel.mockResolvedValue(updatedLevelContent);
    mockDeleteAssignmentTeacherCriterionLevel.mockResolvedValue(deletedLevelContent);
    mockDeleteAssignmentTeacherCriterion.mockResolvedValue(deletedCriterionContent);
    const user = userEvent.setup();
    const onContentChange = vi.fn();

    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={content}
        canCompose={true}
        onContentChange={onContentChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: /edit local rigor/i }));
    await user.clear(screen.getByLabelText('Criterion title', { selector: '#edit-criterion-title-701' }));
    await user.type(
      screen.getByLabelText('Criterion title', { selector: '#edit-criterion-title-701' }),
      'Local rigor revised',
    );
    await user.clear(screen.getByLabelText('Weight', { selector: '#edit-criterion-weight-701' }));
    await user.type(
      screen.getByLabelText('Weight', { selector: '#edit-criterion-weight-701' }),
      '3',
    );
    await user.click(screen.getByRole('button', { name: /save criterion/i }));

    await waitFor(() =>
      expect(mockUpdateAssignmentTeacherCriterion).toHaveBeenCalledWith(
        1,
        701,
        expect.objectContaining({
          title: 'Local rigor revised',
          weight: 3,
        }),
      ),
    );

    await user.click(screen.getByRole('button', { name: /edit exceeds/i }));
    await user.clear(screen.getByLabelText('Level label', { selector: '#edit-level-label-901' }));
    await user.type(
      screen.getByLabelText('Level label', { selector: '#edit-level-label-901' }),
      'Outstanding',
    );
    await user.clear(screen.getByLabelText('Points', { selector: '#edit-level-points-901' }));
    await user.type(
      screen.getByLabelText('Points', { selector: '#edit-level-points-901' }),
      '5',
    );
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() =>
      expect(mockUpdateAssignmentTeacherCriterionLevel).toHaveBeenCalledWith(
        1,
        701,
        901,
        expect.objectContaining({
          label: 'Outstanding',
          points: 5,
        }),
      ),
    );

    await user.click(screen.getByRole('button', { name: /remove exceeds/i }));
    await waitFor(() =>
      expect(mockDeleteAssignmentTeacherCriterionLevel).toHaveBeenCalledWith(1, 701, 901),
    );

    await user.click(screen.getByRole('button', { name: /remove local rigor/i }));
    await waitFor(() => expect(mockDeleteAssignmentTeacherCriterion).toHaveBeenCalledWith(1, 701));

    expect(onContentChange).toHaveBeenNthCalledWith(1, updatedCriterionContent);
    expect(onContentChange).toHaveBeenNthCalledWith(2, updatedLevelContent);
    expect(onContentChange).toHaveBeenNthCalledWith(3, deletedLevelContent);
    expect(onContentChange).toHaveBeenNthCalledWith(4, deletedCriterionContent);
  });

  it('reuses, uploads, and removes teacher-question images through the assignment APIs', async () => {
    mockListReusableAssignmentImages.mockResolvedValue([
      {
        id: 'img-1',
        url: '/img.png',
        originalFilename: 'img.png',
        mimeType: 'image/png',
        sizeBytes: 1024,
      },
    ]);
    mockReuseAssignmentQuestionImage.mockResolvedValue({
      id: 'img-1',
      url: '/img.png',
      originalFilename: 'img.png',
      mimeType: 'image/png',
      sizeBytes: 1024,
    });
    mockUploadAssignmentQuestionImage.mockResolvedValue({
      id: 'img-2',
      url: '/img-2.png',
      originalFilename: 'img-2.png',
      mimeType: 'image/png',
      sizeBytes: 2048,
    });
    mockDeleteAssignmentQuestionImage.mockResolvedValue(undefined);
    const user = userEvent.setup();

    renderComposer();

    await user.click(screen.getByRole('button', { name: /teacher prompt/i }));
    await user.click(screen.getByRole('button', { name: 'reuse-image' }));
    await waitFor(() => expect(mockListReusableAssignmentImages).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(mockReuseAssignmentQuestionImage).toHaveBeenCalledWith(1, 102, 'img-1'),
    );

    await user.click(screen.getByRole('button', { name: 'upload-image' }));
    await waitFor(() =>
      expect(mockUploadAssignmentQuestionImage).toHaveBeenCalledWith(1, 102, expect.any(File)),
    );

    await user.click(screen.getByRole('button', { name: 'remove-image' }));
    await waitFor(() => expect(mockDeleteAssignmentQuestionImage).toHaveBeenCalledWith(1, 102));
  });

  it('keeps local authoring entry points disabled when compose access is off', async () => {
    render(
      <AssignmentComposerPanel
        assignmentId={1}
        content={makeContent()}
        canCompose={false}
        onContentChange={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /shared rubric/i }));
    await screen.findByText('Locked Research Rubric');
    expect(screen.getByRole('button', { name: /add local question/i })).toBeDisabled();
    expect(
      screen.getByRole('button', {
        name: /new local question/i,
      }),
    ).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: /teacher prompt/i }));
    expect(screen.getByLabelText('Prompt', { selector: '#edit-question-prompt-102' })).toBeDisabled();
  });
});
