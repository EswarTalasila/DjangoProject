import { AssessmentDTO, QuestionDTO } from './assessment-service';
import { AssignmentDTO } from './assignment.service';

export const MOCK_ASSESSMENTS: AssessmentDTO[] = [
  {
    id: 1,
    title: 'Math Basics Quiz',
    gradingMode: 'AUTO',
    createdByAdminId: 101,
    questions: [
      {
        id: 11,
        type: 'MULTIPLE_CHOICE',
        prompt: 'What is 2 + 2?',
        maxPoints: 5,
        autoGradable: true,
        choices: [
          { text: '3', score: 0 },
          { text: '4', score: 1 },
          { text: '5', score: 0 },
        ],
        correctAnswers: [1],
      },
      {
        id: 12,
        type: 'SHORT_ANSWER',
        prompt: 'Write the square root of 16.',
        maxPoints: 5,
        autoGradable: false,
      },
      {
        id: 13,
        type: 'NUMBER_SCALE',
        prompt: 'Rate your confidence in math on a scale 1–10.',
        maxPoints: 5,
        autoGradable: true,
        min: 1,
        max: 10,
      },
    ],
  },
  {
    id: 2,
    title: 'Science Quiz',
    gradingMode: 'MANUAL',
    createdByAdminId: 101,
    questions: [
      {
        id: 21,
        type: 'SHORT_ANSWER',
        prompt: 'What planet is known as the Red Planet?',
        maxPoints: 10,
        autoGradable: false,
      },
    ],
  },
];

export const MOCK_ASSIGNMENTS: AssignmentDTO[] = [
  {
    id: 101,
    assessmentId: 1,
    audienceType: 'COURSE',
    courseId: 3001,
    openAt: new Date(Date.now() - 86400000).toISOString(),
    dueAt: new Date(Date.now() + 86400000 * 3).toISOString(),
    submissionStatus: 'NOT_STARTED',
    assessment: MOCK_ASSESSMENTS[0],
  },
  {
    id: 102,
    assessmentId: 2,
    audienceType: 'COURSE',
    courseId: 3001,
    openAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    dueAt: new Date(Date.now() + 86400000 * 5).toISOString(),
    submissionStatus: 'SUBMITTED',
    assessment: MOCK_ASSESSMENTS[1],
  },
];
