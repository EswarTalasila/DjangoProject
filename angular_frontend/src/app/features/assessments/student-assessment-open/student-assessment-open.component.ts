import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import {
  AssignmentService,
  AssignmentDTO,
  SubmissionDTO,
  AnswerDTO,
} from '../../../../services/assignment.service';
import {
  AssessmentService,
  AssessmentDTO,
} from '../../../../services/assessment-service';
import { DialogService } from '../../../../services/dialog.service';

interface LocalAnswer {
  questionId: number;
  type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE' | 'MOOD_METER';

  // Multiple Choice
  selected?: number[];

  // Short Answer
  text?: string;

  // Scale
  val?: number;

  // Mood Meter
  row?: number;
  col?: number;
}

@Component({
  selector: 'app-student-assessment-open',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './student-assessment-open.component.html',
  styleUrl: './student-assessment-open.component.scss',
})
export class StudentAssessmentOpenComponent implements OnInit {
  assignmentId!: number;
  assignment?: AssignmentDTO;
  assessment?: AssessmentDTO;
  answers: Map<number, LocalAnswer> = new Map();

  loading = true;
  error = '';
  submitting = false;
  savingDraft = false;
  submitted = false;

  studentId!: number;
  existingSubmission?: SubmissionDTO;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private assignmentService: AssignmentService,
    private assessmentService: AssessmentService,
    private dialogService: DialogService
  ) {}

  ngOnInit() {
    const studentIdParam = this.route.snapshot.paramMap.get('studentId');
    this.studentId = studentIdParam ? Number(studentIdParam) : 1;
    this.route.params.subscribe((params) => {
      this.assignmentId = +params['assignmentId'];
      this.loadAssignment();
    });
  }

  loadAssignment() {
    this.loading = true;
    this.error = '';

    this.assignmentService.getAssignmentById(this.assignmentId).subscribe({
      next: (assignment) => {
        this.assignment = assignment;
        this.loadAssessment(assignment.assessmentId);
        this.loadExistingSubmission();
      },
      error: (err) => {
        console.error('Error loading assignment:', err);
        this.error = 'Failed to load assignment.';
        this.loading = false;
      },
    });
  }

  loadAssessment(assessmentId: number) {
    this.assessmentService.getAssessmentById(assessmentId).subscribe({
      next: (assessment) => {
        this.assessment = assessment;
        this.initializeAnswers();
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading assessment:', err);
        this.error = 'Failed to load assessment details.';
        this.loading = false;
      },
    });
  }

  loadExistingSubmission() {
    this.assignmentService
      .getStudentSubmission(this.studentId, this.assignmentId)
      .subscribe({
        next: (submission) => {
          if (submission) {
            this.existingSubmission = submission;
            this.loadAnswersFromSubmission(submission);
          }
        },
        error: (err) => {
          if (err.status !== 404) {
            console.error('Error loading submission:', err);
          }
        },
      });
  }

  loadAnswersFromSubmission(submission: SubmissionDTO) {
    submission.answers.forEach((answer) => {
      const localAnswer: LocalAnswer = {
        questionId: answer.questionId,
        type: answer.type,
      };

      switch (answer.type) {
        case 'MULTIPLE_CHOICE':
          localAnswer.selected = answer.data['selected'] as number[];
          break;
        case 'SHORT_ANSWER':
          localAnswer.text = answer.data['text'] as string;
          break;
        case 'NUMBER_SCALE':
          localAnswer.val = answer.data['val'] as number;
          break;
        case 'MOOD_METER':
          localAnswer.row = answer.data['row'] as number;
          localAnswer.col = answer.data['col'] as number;
          break;
      }

      this.answers.set(answer.questionId, localAnswer);
    });
  }

  initializeAnswers() {
    if (!this.assessment) return;

    this.assessment.questions.forEach((question) => {
      console.log(question);
      console.log(question.questionId);
      if (!question.questionId) return;

      console.log(this.answers);
      console.log(this.answers.has(question.questionId));
      if (!this.answers.has(question.questionId)) {
        const answer: LocalAnswer = {
          questionId: question.questionId,
          type: question.type,
        };

        console.log(question.type);
        switch (question.type) {
          case 'MULTIPLE_CHOICE':
            answer.selected = [];
            console.log(answer.selected);
            break;
          case 'SHORT_ANSWER':
            answer.text = '';
            break;
          case 'NUMBER_SCALE':
            answer.val = undefined;
            break;
        }

        this.answers.set(question.questionId, answer);
        console.log(this.answers);
      }
    });
  }

  getAnswer(questionId: number): LocalAnswer | undefined {
    return this.answers.get(questionId);
  }

  updateMultipleChoiceAnswer(
    questionId: number,
    choiceIndex: number,
    selectAll: boolean
  ) {
    console.log("updating...");
    const answer = this.answers.get(questionId);
    console.log(answer);
    if (!answer || !answer.selected) return;

    if (selectAll) {
      const index = answer.selected.indexOf(choiceIndex);
      if (index > -1) {
        answer.selected.splice(index, 1);
      } else {
        answer.selected.push(choiceIndex);
      }
    } else {
      answer.selected = [choiceIndex];
    }

    this.answers.set(questionId, answer);
  }

  isChoiceSelected(questionId: number, choiceIndex: number): boolean {
    const answer = this.answers.get(questionId);
    return answer?.selected?.includes(choiceIndex) || false;
  }

  updateShortAnswer(questionId: number, text: string) {
    const answer = this.answers.get(questionId);
    if (!answer) return;
    answer.text = text;
    this.answers.set(questionId, answer);
  }

  updateNumberScale(questionId: number, value: number) {
    const answer = this.answers.get(questionId);
    if (!answer) return;
    answer.val = value;
    this.answers.set(questionId, answer);
  }

  getNumberScaleValue(questionId: number): number | undefined {
    return this.answers.get(questionId)?.val;
  }

  convertToAnswerDTOs(): AnswerDTO[] {
    const answerDTOs: AnswerDTO[] = [];

    this.answers.forEach((localAnswer) => {
      const answerDTO: AnswerDTO = {
        questionId: localAnswer.questionId,
        type: localAnswer.type,
        data: {},
      };

      switch (localAnswer.type) {
        case 'MULTIPLE_CHOICE':
          answerDTO.data = { selected: localAnswer.selected || [] };
          break;
        case 'SHORT_ANSWER':
          answerDTO.data = { text: localAnswer.text || '' };
          break;
        case 'NUMBER_SCALE':
          answerDTO.data = { val: localAnswer.val };
          break;
        case 'MOOD_METER':
          answerDTO.data = { row: localAnswer.row, col: localAnswer.col };
          break;
      }

      answerDTOs.push(answerDTO);
    });

    return answerDTOs;
  }

  saveDraft() {
    this.savingDraft = true;
    const answersArray = this.convertToAnswerDTOs();

    this.assignmentService
      .saveDraft(this.studentId, this.assignmentId, answersArray)
      .subscribe({
        next: () => {
          this.savingDraft = false;
          this.dialogService.showRobustDialog(
            'Success',
            'Draft saved successfully!',
            'success',
            () => {
              this.router.navigate([`/${this.studentId}/assignments`]);
            }
          );
        },
        error: (err: any) => {
          console.error('Error saving draft:', err);
          this.savingDraft = false;
          this.dialogService.showRobustDialog(
            'Error',
            'Failed to save draft. Please try again.',
            'error'
          );
        },
      });
  }

  submitAssessment() {
    if (!this.validateAnswers()) {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please answer all required questions before submitting.',
        'error'
      );
      return;
    }

    this.dialogService.showRobustDialog(
      'Confirm Submission',
      'Are you sure you want to submit? You cannot change your answers after submission.',
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.submitting = true;
          const answersArray = this.convertToAnswerDTOs();

          const submission: SubmissionDTO = {
            assignmentId: this.assignmentId,
            studentId: this.studentId,
            answers: answersArray,
            status: 'SUBMITTED',
          };

          console.log(submission);
          this.assignmentService
            .submitAssignment(this.assignmentId, submission)
            .subscribe({
              next: (result) => {
                this.submitting = false;
                this.submitted = true;
                this.existingSubmission = result;
                this.dialogService.showRobustDialog(
                  'Success',
                  'Assessment submitted successfully!',
                  'success',
                  () => {
                    this.router.navigate([`/${this.studentId}/assignments`]);
                  }
                );
              },
              error: (err) => {
                console.error('Error submitting assessment:', err);
                this.submitting = false;
                this.dialogService.showRobustDialog(
                  'Error',
                  'Failed to submit assessment. Please try again.',
                  'error'
                );
              },
            });
        }
      }
    );
  }

  validateAnswers(): boolean {
    if (!this.assessment) return false;

    for (const question of this.assessment.questions) {
      if (!question.questionId) continue;

      const answer = this.answers.get(question.questionId);
      if (!answer) return false;

      switch (question.type) {
        case 'MULTIPLE_CHOICE':
          if (!answer.selected || answer.selected.length === 0) {
            return false;
          }
          break;
        case 'SHORT_ANSWER':
          if (!answer.text || answer.text.trim() === '') {
            return false;
          }
          break;
        case 'NUMBER_SCALE':
          if (answer.val === undefined || answer.val === null) {
            return false;
          }
          break;
      }
    }

    return true;
  }

  goBack() {
    this.router.navigate([`/${this.studentId}/assignments`]);
  }

  getDaysRemaining(): number | null {
    if (!this.assignment?.dueAt) return null;
    const due = new Date(this.assignment.dueAt);
    const now = new Date();
    const diff = due.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  formatDueDate(): string {
    if (!this.assignment?.dueAt) return 'No due date';
    const due = new Date(this.assignment.dueAt);
    return due.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  isOverdue(): boolean {
    if (!this.assignment?.dueAt) return false;
    return new Date(this.assignment.dueAt) < new Date();
  }

  canSubmit(): boolean {
    const status = this.existingSubmission?.status;
    return (
      !this.submitted &&
      !this.isOverdue() &&
      (status === undefined || status === 'NOT_STARTED' || status === 'IN_PROGRESS')
    );
  }

  canEdit(): boolean {
    const status = this.existingSubmission?.status;
    return status === undefined || status === 'NOT_STARTED' || status === 'IN_PROGRESS';
  }

  getChoiceText(choice: any): string {
    return typeof choice === 'string' ? choice : choice.prompt;
  }
}
