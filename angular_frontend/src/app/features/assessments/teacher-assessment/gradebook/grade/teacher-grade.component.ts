// teacher-grade.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import {
  AssignmentService,
  SubmissionDTO,
  AssignmentDTO,
} from '../../../../../../services/assignment.service';
import { AssessmentDTO, AssessmentService, QuestionDTO } from '../../../../../../services/assessment-service';
import { CourseService } from '../../../../../../services/course.service';
import { getMoodName, getMoodQuadrant } from '../../../../../../services/mood-meter-mapping';
import { forkJoin } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
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
  selector: 'app-teacher-grade',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './teacher-grade.component.html',
  styleUrl: './teacher-grade.component.scss',
})
export class TeacherGradeComponent implements OnInit {
  teacherId: number | null = null;
  submissionId: number | null = null;

  submission: SubmissionDTO | null = null;
  assessment: AssessmentDTO | null = null;
  rubric: AssessmentDTO | null = null;
  isMoodMeter: boolean = false;
  
  answers: Map<number, LocalAnswer> = new Map();
  rubricScores: Map<number | undefined, number> = new Map();
  rubricIndexToId: Map<number, number> = new Map();
  
  // For accordion functionality
  expandedQuestionId: number | undefined | null = null;
  expandedRubricQuestionId: number | undefined | null = null;

  constructor(
    private assignmentService: AssignmentService,
    private assessmentService: AssessmentService,
    private courseService: CourseService,
    public router: Router,
    private route: ActivatedRoute,
    private dialogService: DialogService
  ) {}

  ngOnInit(): void {
    const teacherIdParam = this.route.snapshot.paramMap.get('teacherId');
    this.teacherId = teacherIdParam ? parseInt(teacherIdParam, 10) : null;

    const submissionIdParam = this.route.snapshot.paramMap.get('submissionId');
    this.submissionId = submissionIdParam ? parseInt(submissionIdParam, 10) : null;
    
    this.loadSubmission();
  }

  loadSubmission() {
    if(this.submissionId !== null) {
      this.assignmentService.getSubmissionById(this.submissionId).subscribe({
        next: (submission) => {
        this.loadAnswersFromSubmission(submission);
          this.submission = submission;
          this.assignmentService.getAssignmentById(submission.assignmentId).subscribe({
            next: (assignment) => {
              this.assessmentService.getAssessmentById(assignment.assessmentId).subscribe({
                next: (assessment) => {
                  console.log('Got assessment', assessment);

                  // Check if this is a Mood Meter assessment
                  this.isMoodMeter = assessment.gradingMode === 'MOOD_METER';

                  // Remove Multiple Choice questions if gradingMode is HYBRID
                  if (assessment.gradingMode === 'HYBRID') {
                    console.log(assessment.questions);
                    assessment.questions = assessment.questions.filter(
                      (q) => q.type !== 'MULTIPLE_CHOICE'
                    );
                    assessment.questions = assessment.questions.filter(
                      (q) => q.data?.['target'] === undefined || q.data?.['target'] === null
                    );
                  }

                  this.assessment = assessment;
                  
                  // Only load rubric if not a Mood Meter assessment
                  if(!this.isMoodMeter) {
                    if(assessment.rubricId !== undefined) {
                      this.assessmentService.getAssessmentById(assessment.rubricId).subscribe({
                        next: (rubric) => {
                          this.rubric = rubric;
                          rubric.questions.forEach((value, index) => {
                            if(value.questionId) {
                              this.rubricIndexToId.set(index, value.questionId);
                            }
                          });
                          console.log(Array.from(this.rubricIndexToId.entries()));
                        },
                        error: (err) => {
                          console.error('Failed to load rubric:', err);
                        }
                      })
                    }
                    else {
                      this.dialogService.showRobustDialog(
                        'Error',
                        'This submission does not have a rubric. Please contact an administrator.',
                        'error'
                      );
                    }
                  }
                },
                error: (err) => {
                  console.error('Failed to load assessment:', err);
                }
              });
            },
            error: (err) => {
              console.error('Failed to load assignment:', err);
            }
          });
        },
        error: (err) => {
          console.error('Failed to load submission:', err);
        }
      });
    }
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

  updateRubricScore(id: number | undefined, event: Event) {
    if (!id) return;

    const input = event.target as HTMLInputElement;
    const value = parseFloat(input.value);

    if (!isNaN(value)) {
      this.rubricScores.set(id, value);
    } else {
      this.rubricScores.delete(id);
    }

    console.log('Updated rubric Scores', Array.from(this.rubricScores.entries()));
  }

  submitScores() {
    let submit: number[] = [];
    this.rubricIndexToId.forEach((questionId, index) => {
      const score = this.rubricScores.get(questionId) ?? 0;
      submit[index] = score;
    });
    if(this.submissionId) {
      this.assignmentService.submitScores(this.submissionId, submit).subscribe({
        next: (response) => {
          console.log('Scores submitted:', response);
          this.navigateBack();
        },
        error: (err) => {
          console.error('Failed to submit scores:', err);
        }
      });
    }
  }

  navigateBack(){
    this.router.navigate([
      '/teacher',
      this.teacherId,
      this.route.snapshot.paramMap.get('courseId'),
      this.route.snapshot.paramMap.get('assignmentId'),
      'gradelist'
    ]);
  }

  /**
   * Get the mood name from row and col coordinates
   */
  getMoodName(row: number, col: number): string {
    return getMoodName(row, col);
  }

  /**
   * Get the mood quadrant description
   */
  getMoodQuadrant(row: number, col: number): string {
    return getMoodQuadrant(row, col);
  }

  /**
   * Get all mood meter answers for a question from the submission
   * Since multiple moods can be selected, we get them directly from the submission
   */
  getMoodMeterAnswers(questionId: number): Array<{row: number, col: number}> {
    if (!this.submission || !this.submission.answers) {
      return [];
    }
    
    return this.submission.answers
      .filter(answer => answer.questionId === questionId && answer.type === 'MOOD_METER')
      .map(answer => ({
        row: answer.data['row'] as number,
        col: answer.data['col'] as number
      }));
  }
}