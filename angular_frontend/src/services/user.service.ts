import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BehaviorSubject } from 'rxjs';

export interface User {
  id?: number;
  firstName: string;
  lastName: string;
  name?: string;
  username: string;
  password?: string | null;
  role?: 'ROLE_ADMIN' | 'ROLE_TEACHER' | 'ROLE_STUDENT';
}

@Injectable({ providedIn: 'root' })
export class UserService {
  constructor(private http: HttpClient) {}

  uploadUsers(users: User[]): Observable<any> {
    console.log('Bulk user payload:', users);
    return this.http.post('/api/v1/auth/create/bulk', users, {
      withCredentials: true,
    });
  }

  /**
   * Edit user by username
   * @param editRequest - Contains loginDto, registerDto, and roleDto
   * @returns Observable with success message
   */
  editUser(
    user: User, id: number
  ): Observable<string> {
    return this.http.post<string>(`/api/v1/auth/edituser/${id}`, user, {
      withCredentials: true,
      responseType: 'text' as 'json'
    });
  }

  private userRoleSubject = new BehaviorSubject<string | null>(
    localStorage.getItem('userRole')
  );

  // Get the current role as an observable
  getUserRole() {
    return this.userRoleSubject.asObservable();
  }

  // Set the user role and notify subscribers
  setUserRole(role: string) {
    localStorage.setItem('userRole', role);
    this.userRoleSubject.next(role);
  }

  // Checks if current user role is within the array.  Used for granting access to pages.
  hasUserRole(roles: Array<string>): boolean {
    const role = localStorage.getItem('userRole');
    if(!role) {
      return false;
    }

    return roles.includes(role);
  }

  // Clear the user role
  clearUserRole() {
    localStorage.removeItem('userRole');
    this.userRoleSubject.next(null);
    localStorage.removeItem('userId');
    localStorage.removeItem('token');
  }

  private userIdSubject = new BehaviorSubject<string | null>(
    localStorage.getItem('userId')
      ? String(localStorage.getItem('userId'))
      : null
  );

  // Get the current userId as an observable
  getUserId() {
    return this.userIdSubject.asObservable();
  }

  // Set the userId and notify subscribers
  setUserId(userId: string) {
    localStorage.setItem('userId', userId.toString());
    this.userIdSubject.next(userId);
  }

  // Clear the userId
  clearUserId() {
    localStorage.removeItem('userId');
    this.userIdSubject.next(null);
  }

  //used to retrieve teachers for filtering on the dashboard
  getTeachersAndAdmins(): Observable<any[]> {
    return this.http.get<any[]>('/api/v1/auth/teachers-admins');
  }
}
