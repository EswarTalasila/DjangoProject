import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AssessmentDTO {
  id: number;
  title: string;
  gradingMode: 'AUTO' | 'MANUAL' | 'HYBRID' | 'RUBRIC' | 'REFLECTION' | 'MOOD_METER';
  createdByAdminId?: number;
  questions: QuestionDTO[];

  rubricId?: number;
  rubricAssessmentIds?: number[];
  category?: string;
}

export interface QuestionDTO {
  questionId?: number;
  id?: number;
  type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'NUMBER_SCALE' | 'MOOD_METER';
  prompt: string;
  maxPoints: number;
  graded?: boolean;
  autoGradable: boolean;
  data?: { [key: string]: any };

  // Multiple Choice specific
  choices?: { prompt: string; score: number }[];
  selectAll?: boolean;
  correctAnswers?: number[];

  // Scale specific
  min?: number;
  max?: number;
  target?: number;

  // Short Answer specific
  caseSensitive?: boolean;
  trim?: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class AssessmentService {
  private baseUrl = '/api/v1/assessments';

  constructor(private http: HttpClient) {}

  getAllAssessments(): Observable<AssessmentDTO[]> {
    return this.http.get<AssessmentDTO[]>(this.baseUrl);
  }

  getAssessmentById(id: number): Observable<AssessmentDTO> {
    return this.http.get<AssessmentDTO>(`${this.baseUrl}/${id}`);
  }

  createAssessment(assessment: AssessmentDTO): Observable<AssessmentDTO> {
    return this.http.post<AssessmentDTO>(this.baseUrl, assessment, {
      headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
    });
  }

  updateAssessment(
    id: number,
    assessment: AssessmentDTO
  ): Observable<AssessmentDTO> {
    return this.http.put<AssessmentDTO>(`${this.baseUrl}/${id}`, assessment, {
      headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
    });
  }

  deleteAssessment(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/${id}`, {
      responseType: 'text',
    });
  }

  assignAssessment(assessmentId: number, assignmentData: any): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/${assessmentId}/assign`,
      assignmentData,
      {
        headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
      }
    );
  }
}
