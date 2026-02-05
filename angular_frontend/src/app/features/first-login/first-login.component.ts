import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors, ReactiveFormsModule, AbstractControlOptions } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-first-login',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './first-login.component.html',
  styleUrl: './first-login.component.scss'
})
export class FirstLoginComponent implements OnInit {
  passwordForm: FormGroup;
  error: string | null = null;
  success: string | null = null;

  userId!: number;

  private apiUrl = '/api/v1/auth/users';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private http: HttpClient
  ) {
    this.passwordForm = this.fb.group(
      {
        password: ['', [Validators.required, Validators.minLength(8)]],
        confirmPassword: ['', Validators.required]
      },
      { validators: this.passwordsMatch } as AbstractControlOptions
    );
  }

  ngOnInit(){
      this.userId = this.route.snapshot.params['userId'];
  }

  passwordsMatch(group: AbstractControl): ValidationErrors | null {
    const password = group.get('password')?.value;
    const confirmPassword = group.get('confirmPassword')?.value;
    return password === confirmPassword ? null : { notMatching: true };
  }

  onSubmit() {
    if (this.passwordForm.invalid) {
      this.error = 'Please fix the errors in the form.';
      return;
    }

    const password = this.passwordForm.get('password')?.value;

    this.http
    .post(`${this.apiUrl}/${this.userId}/set-password`, password, {
      withCredentials: true,
      observe: 'response',
      responseType: 'text',
    })
    .subscribe({
      next: (response) => {
        if (response.status === 200) {
          this.success = 'Password set successfully! Redirecting to login...';
          this.error = null;
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 2000);
        } else {
          console.warn('Unexpected response status:', response.status);
          this.error = `Unexpected status: ${response.status}`;
          this.success = null;
        }
      },
      error: (err) => {
        console.error('Error setting password:', err);
        this.error = err?.error ?? (err?.message || 'Failed to set password');
        this.success = null;
      },
    });
  }
}
