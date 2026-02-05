import { Component } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { UserService } from '../../../services/user.service';
import { DialogService } from '../../../services/dialog.service';

declare const google: any;

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  email = '';
  password = '';
  showPasswordField = false;

  private apiUrl = '/api/v1/auth';

  private clientId =
    '505506154303-dh602eml7suv0h46fu9ese7kopbn6sq7.apps.googleusercontent.com';

  constructor(
    private http: HttpClient,
    private router: Router,
    private userService: UserService,
    private dialogService: DialogService
  ) {}

  ngOnInit() {
    this.userService.clearUserRole();
    console.log("This: ", localStorage.getItem('userRole'));
  }

  signInWithGoogle() {
    const tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: this.clientId,
      scope: 'email profile openid',
      callback: (response: any) => this.handleCredentialResponse(response),
    });

    tokenClient.requestAccessToken();
  }

  handleCredentialResponse(response: any) {
    console.log('Raw response from Google:', response);
    const accessToken = response.access_token;
    console.log('Access token:', accessToken);

    this.http
      .post<{
        accessToken: string;
        tokenType: string;
        role: string;
        id: string;
      }>(`${this.apiUrl}/google`, { accessToken }, { withCredentials: true })
      .subscribe({
        next: (res) => {
          localStorage.setItem('token', res.accessToken);

          console.log('Logged in user:', res);
          if (res.role == 'STUDENT') {
            this.router.navigate([`${res.id}/assignments`]);
          } else {
            this.router.navigate(['/dashboard']);
          }
          this.userService.setUserRole(res.role);
          this.userService.setUserId(res.id);
        },
        error: (err: HttpErrorResponse) => {
          const msg = err?.error?.error || err?.message || 'Login failed';
          this.dialogService.showRobustDialog(
            'Error',
            msg,
            'error'
          );
          console.error('Login failed:', err);
        },
      });
  }

  checkEmail() {
    if (!this.email) {
      this.dialogService.showRobustDialog(
        'Validation Error',
        'Please enter an email address.',
        'error'
      );
      return;
    }

    this.http
      .post(`${this.apiUrl}/check-email`, { email: this.email })
      .subscribe({
        next: (res: any) => {
          if (!res.exists) {
            this.dialogService.showRobustDialog(
              'Error',
              'No account found with this email.',
              'error'
            );
            return;
          }

          if (res.needsPassword) {
            if (res.userId) {
              this.router.navigate([`/first-login/${res.userId}`]);
            } else {
              console.error('User ID missing in response');
              this.dialogService.showRobustDialog(
                'Error',
                'An error occurred. Please try again.',
                'error'
              );
            }
          } else {
            this.showPasswordField = true;
          }
        },
        error: (err) => {
          console.error('Check email failed:', err);
          if (err.status === 404) {
            this.dialogService.showRobustDialog(
              'Error',
              'No account found with this email.',
              'error'
            );
          } else {
            this.dialogService.showRobustDialog(
              'Error',
              'An error occurred. Please try again.',
              'error'
            );
          }
        },
      });
  }

  resetPassword() {
    this.http
      .post(`${this.apiUrl}/check-email`, { email: this.email })
      .subscribe({
        next: (res: any) => {
          if (!res.exists) {
            this.dialogService.showRobustDialog(
              'Error',
              'No account found with this email.',
              'error'
            );
            return;
          }

          this.router.navigate([`/first-login/${res.userId}`]);
        },
      });
  }

  onSubmit(event: Event) {
    event.preventDefault();

    this.http
      .post<{
        accessToken: string;
        tokenType: string;
        role: string;
        id: string;
      }>(
        `${this.apiUrl}/login`,
        {
          username: this.email,
          password: this.password,
        },
        { withCredentials: true }
      )
      .subscribe({
        next: (res) => {
          localStorage.setItem('token', res.accessToken);
          console.log('Logged in user:', res);

          this.userService.setUserRole(res.role);
          this.userService.setUserId(res.id);

          if (res.role == 'STUDENT') {
            this.router.navigate([`${res.id}/assignments`]);
          } else {
            this.router.navigate(['/dashboard']);
          }
        },
        error: (err: HttpErrorResponse) => {
          const msg = err?.error ?? (err?.message || 'Login failed');
          this.dialogService.showRobustDialog(
            'Error',
            msg,
            'error'
          );
          console.error('Login failed:', err);
        },
      });
  }
}