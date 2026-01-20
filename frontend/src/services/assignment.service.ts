import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin, of } from 'rxjs';
import { switchMap, map, catchError } from 'rxjs/operators';
import { AssessmentDTO, AssessmentService } from './assessment-service';

export interface AssignmentDTO {
  id: number;
  assessmentId: number;
  audienceType: 'COURSE' | 'TEACHER';
  courseId?: number;
  teacherId?: number;
  openAt: string;
  dueAt?: string;

  assessment?: AssessmentDTO;
  assessmentName?: string;
  submissionStatus?: 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'GRADED';
}

export interface SubmissionDTO {
  id?: number;
  assignmentId: number;
  studentId?: number;
  teacherId?: number;
  submittedAt?: string;
  score?: number;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'GRADED';
  answers: AnswerDTO[];

  studentName?: string;
}

export interface AnswerDTO {
  questionId: number;
  type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE' | 'MOOD_METER';
  data: { [key: string]: any };
}

export interface CreateSubmissionRequestDTO {
  answers: AnswerDTO[];
}

@Injectable({
  providedIn: 'root',
})
export class AssignmentService {
  private baseUrl = '/api/v1';

  constructor(private http: HttpClient, private assessmentService: AssessmentService) {}

  /**
   * Submits graded scores for a student submission
   */
  submitScores(submissionId: number, scores: number[]): Observable<SubmissionDTO> {
    return this.http.patch<SubmissionDTO>(`${this.baseUrl}/submissions/${submissionId}/override-score`, scores, { withCredentials: true });
  }

  /**
   * Retrieves a submission by its unique ID.
   * @param submissionId - The ID of the submission to retrieve.
   * @returns An Observable of SubmissionDto.
   */
  getSubmissionById(submissionId: number): Observable<SubmissionDTO> {
    return this.http.get<SubmissionDTO>(`${this.baseUrl}/submissions/${submissionId}`);
  }

  /**
   * Gets the submissions tied to an assignment
   * @param assignmentId - The ID of the assignment
   * @returns An Observable of AssignmentDto
   */
  getSubmissionByAssignment(assignmentId: number): Observable<SubmissionDTO[]> {
    return this.http.get<SubmissionDTO[]>(`${this.baseUrl}/assignments/${assignmentId}/submissions`);
  }

  getSubmissionByStudentId(studentId: number): Observable<SubmissionDTO[]> {
    return this.http.get<SubmissionDTO[]>(`${this.baseUrl}/students/${studentId}/submissions`);
  }

  /**
   * Get all assignments for a specific student
   * This will return assignments that are open and available
   */
  getStudentAssignments(studentId: number): Observable<AssignmentDTO[]> {
    return this.http.get<AssignmentDTO[]>(
      `${this.baseUrl}/assignments/users/${studentId}`,
      { withCredentials: true }
    );
  }

  /** * Get all assignments for a specific course */ 
  getAssignmentsByCourse(courseId: String): Observable<AssignmentDTO[]> { 
    return this.http.get<AssignmentDTO[]>( `${this.baseUrl}/assignments/courses/${courseId}`, { withCredentials: true })
    .pipe(
        switchMap(assignments => {
          const assessmentRequests = assignments.map(assignment =>
            this.assessmentService.getAssessmentById(assignment.assessmentId).pipe(
              map(assessment => {
                assignment.assessmentName = assessment.title;
                return assignment;
              })
            )
          );
          return forkJoin(assessmentRequests);
        })
    ); 
  }


  /**
   * Get a specific assignment by ID
   */
  getAssignmentById(assignmentId: number): Observable<AssignmentDTO> {
    return this.http.get<AssignmentDTO>(
      `${this.baseUrl}/assignments/${assignmentId}`,
      { withCredentials: true }
    );
  }

  /**
   * Get student's submission for a specific assignment (if exists)
   */
  getStudentSubmission(
    studentId: number,
    assignmentId: number
  ): Observable<SubmissionDTO | null> {
    return this.http.get<SubmissionDTO>(
      `${this.baseUrl}/students/${studentId}/assignments/${assignmentId}/submission`,
      { withCredentials: true }
    );
  }

  /**
   * Get all self-submissions for a specific teacher
   */
  getTeacherSelfSubmissions(teacherId: number): Observable<SubmissionDTO[]> {
    return this.http.get<SubmissionDTO[]>(
      `${this.baseUrl}/teachers/${teacherId}/submissions`,
      { withCredentials: true }
    ).pipe(
      map((submissions: SubmissionDTO[]) => {
        return submissions;
      })
    );
  }

  /**
   * Submit a teacher's self-assessment to an assessment.
   * @param assessmentId - The ID of the assessment to submit to.
   * @param req - The submission request object containing the teacher's submission data.
   * @returns An observable containing the SubmissionDto after submission.
   */
  submitSelfAssessment(assessmentId: number, req: AnswerDTO[]): Observable<SubmissionDTO> {
    return this.http.post<SubmissionDTO>(`${this.baseUrl}/assessments/${assessmentId}/teacher-self-assess`, req, { withCredentials: true });
  }

  /**
   * Edit/update an existing submission.
   * @param submission - The complete SubmissionDTO with updated answers
   * @returns An observable containing the updated SubmissionDto
   */
  editSubmission(submission: SubmissionDTO): Observable<SubmissionDTO> {
    return this.http.put<SubmissionDTO>(
      `${this.baseUrl}/submissions`, 
      submission, 
      { withCredentials: true }
    );
  }

  /**
   * Submit answers for an assignment
   */
  submitAssignment(
    assignmentId: number,
    submission: SubmissionDTO
  ): Observable<SubmissionDTO> {
    console.log(submission);
    return this.http.post<SubmissionDTO>(
      `${this.baseUrl}/assignments/${assignmentId}/submissions`,
      submission,
      { withCredentials: true }
    );
  }

  /**
   * Save draft answers (partial submission)
   */
  saveDraft(
    studentId: number,
    assignmentId: number,
    answers: AnswerDTO[]
  ): Observable<any> {
    return this.http.put(
      `${this.baseUrl}/students/${studentId}/assignments/${assignmentId}/draft`,
      { answers },
      { withCredentials: true }
    );
  }

  /**
   * Delete an assignment by its ID
   * @param assignmentId - The ID of the assignment to delete
   * @returns An observable containing the success message
   */
  deleteAssignment(assignmentId: number): Observable<string> {
    return this.http.delete<string>(
      `${this.baseUrl}/assignments/${assignmentId}`,
      { withCredentials: true, responseType: 'text' as 'json' }
    );
  }


  /**
   * Create AnswerDTO for Multiple Choice question
   */
  static createMultipleChoiceAnswer(
    questionId: number,
    selectedIndices: number[]
  ): AnswerDTO {
    return {
      questionId,
      type: 'MULTIPLE_CHOICE',
      data: {
        selected: selectedIndices,
      },
    };
  }

  /**
   * Create AnswerDTO for Short Answer question
   */
  static createShortAnswerAnswer(questionId: number, text: string): AnswerDTO {
    return {
      questionId,
      type: 'SHORT_ANSWER',
      data: {
        text: text,
      },
    };
  }

  /**
   * Create AnswerDTO for Number Scale question
   */
  static createNumberScaleAnswer(questionId: number, value: number): AnswerDTO {
    return {
      questionId,
      type: 'NUMBER_SCALE',
      data: {
        val: value,
      },
    };
  }

  /**
   * Create AnswerDTO for Mood Meter question
   */
  static createMoodMeterAnswer(
    questionId: number,
    row: number,
    col: number
  ): AnswerDTO {
    return {
      questionId,
      type: 'MOOD_METER',
      data: {
        row: row,
        col: col,
      },
    };
  }
}
