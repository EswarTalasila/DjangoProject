import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { v4 as uuidv4 } from 'uuid';
import {
  QuestionBase,
  MultipleChoiceQuestion,
  ShortAnswerQuestion,
  ScaleQuestion,
} from '../../../../models/question.model';
import { MultipleChoiceQuestionComponent } from '../../assessments/assessment-template/multiple-choice-question/multiple-choice-question.component';
import { ShortAnswerQuestionComponent } from '../../assessments/assessment-template/short-answer-question/short-answer-question.component';
import { ScaleQuestionComponent } from '../../assessments/assessment-template/scale-question/scale-question.component';
import { GradingCriteriaQuestionComponent } from './grading-criteria-question/grading-criteria-question.component';
import {
  AssessmentService,
  AssessmentDTO,
  QuestionDTO,
} from '../../../../services/assessment-service';
import { DialogService } from '../../../../services/dialog.service';

@Component({
  selector: 'app-assessment-template',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MultipleChoiceQuestionComponent,
    ShortAnswerQuestionComponent,
    ScaleQuestionComponent,
    GradingCriteriaQuestionComponent,
  ],
  templateUrl: './assessment-template.component.html',
  styleUrl: './assessment-template.component.scss',
})
export class AssessmentTemplateComponent implements OnInit {
  questions: QuestionBase[] = [];
  assessmentTitle: string = '';
  assessmentCategory: string = '';
  gradingMode: 'AUTO' | 'MANUAL' | 'HYBRID' | 'RUBRIC' | 'REFLECTION' | 'MOOD_METER' = 'MANUAL';
  availableAssessments: AssessmentDTO[] = [];
  isRubric = false;
  selectedRubricAssessmentId?: number;
  rubricAssessments: number[] = [];

  assessmentId!: number;
  isEditMode = false;

  constructor(
    private assessmentApiService: AssessmentService,
    private route: ActivatedRoute,
    private router: Router,
    private dialogService: DialogService
  ) {}

  ngOnInit() {
    this.loadAvailableAssessments();

    this.route.params.subscribe((params) => {
      const id = params['assessmentId'];
      if (id) {
        this.assessmentId = id;
        this.isEditMode = true;
        this.loadAssessment(this.assessmentId);
      }
    });
  }

  loadAvailableAssessments() {
    this.assessmentApiService.getAllAssessments().subscribe({
      next: (assessments) => {
        this.availableAssessments = assessments.filter(assessment => assessment.gradingMode !== 'RUBRIC' && assessment.gradingMode !== 'MOOD_METER');
      },
      error: (error) => {
        console.error('Error loading assessments:', error);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to load assessments',
          'error'
        );
      },
    });
  }

  loadAssessment(id: number) {
    this.assessmentApiService.getAssessmentById(id).subscribe({
      next: (assessment) => {
        this.assessmentTitle = assessment.title;
        if(assessment.category) {
          this.assessmentCategory = assessment.category;
        }
        this.gradingMode = assessment.gradingMode;
        this.questions = this.convertQuestionsFromDTO(assessment.questions);
        console.log(this.questions);
      },
      error: (error) => {
        console.error('Error loading assessment:', error);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to load assessment',
          'error'
        );
      },
    });
  }

  convertQuestionsFromDTO(dtos: QuestionDTO[]): QuestionBase[] {
    return dtos.map((dto) => {
      const data = dto.data || {};
      let imageValue: string | File | null = null;
      if (data['image'] && typeof data['image'] === 'string') {
        imageValue = data['image'];
      }

      const base = {
        id: dto.id?.toString() || uuidv4(),
        prompt: dto.prompt,
        maxPoints: dto.maxPoints,
        autoGradable: dto.autoGradable,
        graded: dto.graded,
        image: imageValue,
      };

      switch (dto.type) {
        case 'MULTIPLE_CHOICE':
          return {
            ...base,
            type: 'multiple-choice',
            choices: (data['choices'] || []).map((c: any) =>
              typeof c === 'string' ? { prompt: c, score: 0 } : c
            ),
            selectAll: data['selectAll'] || false,
            correctAnswers: data['correctAnswers'] || [],
          } as MultipleChoiceQuestion;

        case 'SHORT_ANSWER':
          return {
            ...base,
            type: 'short-answer',
            caseSensitive: data['caseSensitive'],
            trim: data['trim'],
          } as ShortAnswerQuestion;

        case 'NUMBER_SCALE':
          return {
            ...base,
            type: 'scale',
            min: dto.min || 0,
            max: dto.max || 10,
            target: data['target'],
          } as ScaleQuestion;

        default:
          throw new Error(`Unknown question type: ${dto.type}`);
      }
    });
  }

  addQuestion(type: 'multiple-choice' | 'short-answer' | 'scale') {
    let newQuestion: QuestionBase;

    if (type === 'multiple-choice') {
      newQuestion = {
        id: uuidv4(),
        type,
        prompt: '',
        maxPoints: 10,
        autoGradable: true,
        image: null,
        choices: [
          { prompt: '', score: 0 },
          { prompt: '', score: 0 },
        ],
        selectAll: false,
        correctAnswers: [],
      } as MultipleChoiceQuestion;
    } else if (type === 'short-answer') {
      newQuestion = {
        id: uuidv4(),
        type,
        prompt: '',
        maxPoints: 10,
        autoGradable: false,
        image: null,
        caseSensitive: false,
        trim: true,
      } as ShortAnswerQuestion;
    } else {
      newQuestion = {
        id: uuidv4(),
        type,
        prompt: '',
        maxPoints: 10,
        autoGradable: true,
        image: null,
        min: 0,
        max: 10,
        target: undefined,
      } as ScaleQuestion;
    }

    this.questions.push(newQuestion);
  }

  removeQuestion(index: number) {
    this.dialogService.showRobustDialog(
      'Confirm Removal',
      'Are you sure you want to remove this question?',
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.questions.splice(index, 1);
        }
      }
    );
  }

  async saveAssessment() {
    if (!this.assessmentTitle.trim()) {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please enter an assessment title',
        'error'
      );
      return;
    }

    if (this.questions.length === 0 && this.gradingMode !== 'MOOD_METER') {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please add at least one question',
        'error'
      );
      return;
    }

    if (this.isRubric && !this.selectedRubricAssessmentId) {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please select an assessment for this rubric',
        'error'
      );
      return;
    }

    const questionDTOs: QuestionDTO[] = await Promise.all(
      this.questions.map((q) => this.convertToQuestionDTO(q))
    );

    //TODO: NEED TO BE ABLE TO SELECT MULTIPLE ASSESSMENTS FOR THE SAME RUBRIC
    if (this.selectedRubricAssessmentId && !this.rubricAssessments.includes(this.selectedRubricAssessmentId)) {
      this.rubricAssessments.push(this.selectedRubricAssessmentId);
    }

    const assessmentDTO: AssessmentDTO = {
      id: this.assessmentId,
      title: this.assessmentTitle,
      gradingMode: this.gradingMode,
      questions: questionDTOs,
      rubricAssessmentIds: this.rubricAssessments,
      category: this.assessmentCategory,
    };

    if (this.isEditMode && this.assessmentId) {
      assessmentDTO.id = this.assessmentId;
    }

    const apiCall =
      this.isEditMode && this.assessmentId
        ? this.assessmentApiService.updateAssessment(
            this.assessmentId,
            assessmentDTO
          )
        : this.assessmentApiService.createAssessment(assessmentDTO);
    apiCall.subscribe({
      next: (savedAssessment) => {
        console.log('Assessment saved:', savedAssessment);
        this.dialogService.showRobustDialog(
          'Success',
          `Assessment ${this.isEditMode ? 'updated' : 'created'} successfully!`,
          'success',
          () => {
            this.router.navigate(['/assessments']);
          }
        );
      },
      error: (error) => {
        console.error('Error saving assessment:', error);
        this.dialogService.showRobustDialog(
          'Error',
          'Failed to save assessment. Please try again.',
          'error'
        );
      },
    });
  }

  cancelEdit() {
    this.dialogService.showRobustDialog(
      'Confirm Cancel',
      'Are you sure you want to cancel? Any unsaved changes will be lost.',
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.router.navigate(['/assessments']);
        }
      }
    );
  }

  private async convertToQuestionDTO(
    question: QuestionBase
  ): Promise<QuestionDTO> {
    let imageString: string | null = null;
    if (question.image) {
      if (typeof question.image === 'string') {
        imageString = question.image;
      } else if (question.image instanceof File) {
        imageString = await this.fileToBase64(question.image);
      }
    }

    const baseDTO: QuestionDTO = {
      prompt: question.prompt,
      maxPoints: question.maxPoints,
      autoGradable: question.autoGradable,
      type: this.mapQuestionType(question.type),
    };

    const data: { [key: string]: any } = {};

    if (imageString) {
      data['image'] = imageString;
    }

    if (question.type === 'multiple-choice') {
      const mcq = question as MultipleChoiceQuestion;
      data['choices'] = mcq.choices.map((c) => ({prompt: c.prompt, score: c.score}));
      data['selectAll'] = mcq.selectAll;
      data['correctAnswers'] = mcq.correctAnswers;
      console.log(data);
    } else if (question.type === 'short-answer') {
      const saq = question as ShortAnswerQuestion;
      data['caseSensitive'] = saq.caseSensitive;
      data['trim'] = saq.trim;
    } else {
      const scaleQ = question as ScaleQuestion;
      data['min'] = scaleQ.min;
      data['max'] = scaleQ.max;
      if (scaleQ.target !== undefined) {
        data['target'] = scaleQ.target;
      }
    }

    return {
      ...baseDTO,
      data: data,
    };
  }

  private fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        resolve(reader.result as string);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  private mapQuestionType(
    type: string
  ): 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE' {
    switch (type) {
      case 'multiple-choice':
        return 'MULTIPLE_CHOICE';
      case 'short-answer':
        return 'SHORT_ANSWER';
      case 'scale':
        return 'NUMBER_SCALE';
      default:
        throw new Error(`Unknown question type: ${type}`);
    }
  }
  
  autoExpand(event: Event) {
      const textarea = event.target as HTMLTextAreaElement;
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
      
      // Limit maximum height and enable scrolling if needed
      const maxHeight = 200;
      if (textarea.scrollHeight > maxHeight) {
        textarea.style.height = maxHeight + 'px';
        textarea.style.overflowY = 'auto';
      } else {
        textarea.style.overflowY = 'hidden';
      }
    }
}