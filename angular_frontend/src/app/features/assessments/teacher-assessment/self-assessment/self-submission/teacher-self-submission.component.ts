import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import {
  AssignmentService,
  SubmissionDTO,
  CreateSubmissionRequestDTO,
  AnswerDTO,
} from '../../../../../../services/assignment.service';
import {
  AssessmentService,
  AssessmentDTO,
} from '../../../../../../services/assessment-service';
import { DialogService } from '../../../../../../services/dialog.service';

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
  selector: 'app-teacher-self-submission',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './teacher-self-submission.component.html',
  styleUrl: './teacher-self-submission.component.scss',
})
export class TeacherSelfSubmissionComponent implements OnInit {
  assessmentId!: number;
  submissionId?: number;
  assessment?: AssessmentDTO;
  answers: Map<number, LocalAnswer> = new Map();

  loading = true;
  error = '';
  submitting = false;
  savingDraft = false;
  submitted = false;

  teacherId!: number;
  existingSubmission?: SubmissionDTO;
  isEditMode = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private assignmentService: AssignmentService,
    private assessmentService: AssessmentService,
    private dialogService: DialogService
  ) {}

  ngOnInit() {
    const teacherIdParam = this.route.snapshot.paramMap.get('teacherId');
    this.teacherId = teacherIdParam ? Number(teacherIdParam) : 1;

    this.route.params.subscribe((params) => {
      this.assessmentId = +params['assessmentId'];
      
      // Check if we have a submissionId (edit mode)
      const submissionIdParam = params['submissionId'];
      if (submissionIdParam) {
        this.submissionId = +submissionIdParam;
        this.isEditMode = true;
      }
      
      this.loadAssessment();
    });
  }

  loadAssessment() {
    this.loading = true;
    this.error = '';

    this.assessmentService.getAssessmentById(this.assessmentId).subscribe({
      next: (assessment) => {
        this.assessment = assessment;
        console.log("ASSESSMENT", assessment);
        this.initializeAnswers();
        
        // If we have a submissionId, load the existing submission
        if (this.submissionId) {
          this.loadExistingSubmission(this.submissionId);
        } else {
          this.loading = false;
        }
      },
      error: (err) => {
        console.error('Error loading assessment:', err);
        this.error = 'Failed to load assessment.';
        this.loading = false;
      },
    });
  }

  /**
   * Load an existing submission by ID and populate the form
   */
  loadExistingSubmission(submissionId: number) {
    this.assignmentService.getSubmissionById(submissionId).subscribe({
      next: (submission) => {
        if (submission) {
          this.existingSubmission = submission;
          this.loadAnswersFromSubmission(submission);
          console.log('Loaded existing submission:', submission);
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading existing submission:', err);
        if (err.status !== 404) {
          this.error = 'Failed to load existing submission.';
        }
        this.loading = false;
      },
    });
  }

  /**
   * Populate the form with answers from an existing submission
   * This is adapted from StudentAssessmentOpenComponent
   */
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

      // Update the answers map with the loaded data
      this.answers.set(answer.questionId, localAnswer);
    });
    
    console.log('Answers loaded from submission:', this.answers);
  }

  initializeAnswers() {
    if (!this.assessment) return;

    this.assessment.questions.forEach((question) => {
      if (!question.questionId) return;


      if (!this.answers.has(question.questionId)) {
        const answer: LocalAnswer = {
          questionId: question.questionId,
          type: question.type,
        };

        switch (question.type) {
          case 'MULTIPLE_CHOICE':
            answer.selected = [];
            break;
          case 'SHORT_ANSWER':
            answer.text = '';
            break;
          case 'NUMBER_SCALE':
            answer.val = undefined;
            break;
        }

        this.answers.set(question.questionId, answer);
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

  submitAssessment() {
    if (!this.validateAnswers()) {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please answer all required questions before submitting.',
        'error'
      );
      return;
    }
  
    const confirmMessage = this.isEditMode 
      ? 'Are you sure you want to update your submission?'
      : 'Are you sure you want to submit?';
      
    this.dialogService.showRobustDialog(
      'Confirm Submission',
      confirmMessage,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.submitting = true;
          const answersArray = this.convertToAnswerDTOs();
        
          // If editing an existing submission, use PUT endpoint
          if (this.isEditMode && this.existingSubmission && this.existingSubmission.id) {
            // Build complete SubmissionDTO for editing
            const submissionDto: SubmissionDTO = {
              id: this.existingSubmission.id,
              assignmentId: this.existingSubmission.assignmentId,
              teacherId: this.teacherId,
              answers: answersArray,
              status: 'SUBMITTED'
            };
        
            console.log('Updating submission:', submissionDto);
            
            this.assignmentService.editSubmission(submissionDto).subscribe({
              next: (result: any) => {
                this.submitting = false;
                this.submitted = true;
                this.existingSubmission = result;
                this.dialogService.showRobustDialog(
                  'Success',
                  'Assessment updated successfully!',
                  'success',
                  () => {
                    this.router.navigate([`/teacher/${this.teacherId}/assessments`]);
                  }
                );
              },
              error: (err: any) => {
                console.error('Error updating assessment:', err);
                this.submitting = false;
                this.dialogService.showRobustDialog(
                  'Error',
                  'Failed to update assessment. Please try again.',
                  'error'
                );
              },
            });
          } else {
            // Creating new submission - use POST endpoint
            const submission: CreateSubmissionRequestDTO = {
              answers: answersArray
            };
        
            console.log('Creating new submission:', answersArray);
            
            this.assignmentService
              .submitSelfAssessment(this.assessmentId, answersArray)
              .subscribe({
                next: (result: any) => {
                  this.submitting = false;
                  this.submitted = true;
                  this.existingSubmission = result;
                  this.dialogService.showRobustDialog(
                    'Success',
                    'Assessment submitted successfully!',
                    'success',
                    () => {
                      this.router.navigate([`/teacher/${this.teacherId}/assessments`]);
                    }
                  );
                },
                error: (err: any) => {
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
      }
    );
  }

  validateAnswers(): boolean {
    if (!this.assessment) return false;

    for (const question of this.assessment.questions) {
      if (!question.id) continue;

      const answer = this.answers.get(question.id);
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
    this.router.navigate([`/teacher/${this.teacherId}/self`]);
  }

  goBackToSubmissions() {
    this.router.navigate([`/teacher/${this.teacherId}/assessments`]);
  }

  getChoiceText(choice: any): string {
    return typeof choice === 'string' ? choice : choice.prompt;
  }
}