import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';

export interface Student {
  firstName: string;
  lastName: string;
  username: string;
  courseId: number;
  consent: boolean;
  id?: number;
  name?: string;
}

@Injectable({ providedIn: 'root' })
export class StudentService {

  constructor(private http: HttpClient) {}

  addStudent(student: Student): Observable<any> {
    console.log('Single student payload:', student);
    return this.http.post('/api/v1/students/', student, {withCredentials: true});
  }

  uploadStudents(students: Student[]): Observable<any> {
    console.log('Bulk students payload:', students);
    return this.http.post('/api/v1/students/bulk/', students, {withCredentials: true});
  }

  /**
   * Get all students in a specific course
   */
  getStudentsInCourse(courseId: number): Observable<Student[]> {
    return this.http.get<Student[]>(`/api/v1/courses/${courseId}/students`, {
      withCredentials: true,
    });
  }
}
