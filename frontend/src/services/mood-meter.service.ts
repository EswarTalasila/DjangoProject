import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface MoodSelection {
  row: number;
  col: number;
}

export interface MoodMeterSubmission {
  studentId: string;
  assignmentId?: string;
  moods: MoodSelection[];
  submittedAt?: Date;
}

export interface MoodMeterAssignment {
  id: string;
  title: string;
  description?: string;
  dueDate?: Date;
  status: 'PENDING' | 'SUBMITTED' | 'OVERDUE';
}

@Injectable({
  providedIn: 'root'
})
export class MoodMeterService {
  private baseUrl = '/api/v1';

  constructor(private http: HttpClient) {}


  getMoodMeterAssignments(studentId: string): Observable<MoodMeterAssignment[]> {
    return this.http.get<MoodMeterAssignment[]>(
      `${this.baseUrl}/${studentId}/assignments/mood-meter`,
      { withCredentials: true }
    );
  }

  getMoodMeterAssignment(studentId: string, assignmentId: string): Observable<MoodMeterAssignment> {
    return this.http.get<MoodMeterAssignment>(
      `${this.baseUrl}/${studentId}/assignments/mood-meter/${assignmentId}`,
      { withCredentials: true }
    );
  }

  submitMoodMeter(studentId: string, submission: MoodMeterSubmission): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/${studentId}/submissions/mood-meter`,
      submission,
      { withCredentials: true }
    );
  }

  getStudentSubmissions(studentId: string): Observable<MoodMeterSubmission[]> {
    return this.http.get<MoodMeterSubmission[]>(
      `${this.baseUrl}/${studentId}/submissions/mood-meter`,
      { withCredentials: true }
    );
  }

  getSubmissionsForAssignment(assignmentId: string): Observable<MoodMeterSubmission[]> {
    return this.http.get<MoodMeterSubmission[]>(
      `${this.baseUrl}/assignments/mood-meter/${assignmentId}/submissions`,
      { withCredentials: true }
    );
  }
}