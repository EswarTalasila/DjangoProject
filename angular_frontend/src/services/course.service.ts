import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';

export interface CourseSummaryDTO {
  id: string;
  name: string;
}

export interface StudentDTO {
  id: number;
  name: string;
  username: string;
  consent?: boolean;
  courseId?: number;
}

@Injectable({
  providedIn: 'root',
})
export class CourseService {
  private readonly apiUrl = '/api/v1/courses';

  constructor(private http: HttpClient) {}

  /**
   * Fetches a list of courses for the current user (Teacher or Admin).
   * @returns Observable of a list of CourseSummaryDto
   */
  getCourses(): Observable<HttpResponse<CourseSummaryDTO[]>> {
    return this.http.get<CourseSummaryDTO[]>(`${this.apiUrl}`, {
      observe: 'response' as const
    });
  }

  /**
   * Fetches list of students for a specific course
   * @param courseId - The ID of the course
   * @returns Observable of list of StudentDTO
   */
  getStudentsInCourse(courseId: string): Observable<StudentDTO[]> {
    return this.http.get<StudentDTO[]>(`${this.apiUrl}/${courseId}/students`, {
      withCredentials: true
    });
  }

  /**
   * Removes a student from a course and deletes the student user
   * @param courseId - The ID of the course
   * @param studentUserId - The ID of the student user to remove
   * @returns Observable with success message
   */
  removeStudent(courseId: string, studentUserId: number): Observable<string> {
    return this.http.delete<string>(`${this.apiUrl}/${courseId}/students/${studentUserId}`, {
      withCredentials: true,
      responseType: 'text' as 'json'
    });
  }
}
