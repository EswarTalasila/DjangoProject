import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { User } from '../../../services/user.service';
import { DialogService } from '../../../services/dialog.service';

interface Role {
  id: number;
  name: string;
}


@Component({
  selector: 'app-account',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './account.component.html',
  styleUrl: './account.component.scss'
})

export class AccountComponent {
  admins: User[] = [];
  teachers: User[] = [];

  constructor(private router: Router, private http: HttpClient, private dialogService: DialogService) {}

  ngOnInit(): void {
    this.http.get<User[]>('/api/v1/auth/teachers-admins').subscribe({
      next: (users) => {
        console.log(users);
        this.admins = users.filter(user =>
          user.role === 'ROLE_ADMIN').filter(user => user.username !== 'admin');
        this.teachers = users.filter(user =>
          user.role === 'ROLE_TEACHER'
        );
      },
      error: (err) => {
        console.error('Failed to fetch users:', err);
      }
    });
  }

  onAddUserClick(): void {
    this.router.navigate(['/account/create']);
  }

  deleteUser(username: string): void {
    // Use the new robust dialog method for confirmation
    this.dialogService.showRobustDialog(
      'Confirm Deletion',
      `Are you sure you want to delete ${username}?`,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.http.delete(`/api/v1/auth/user/${username}`, { responseType: 'text' }).subscribe({
            next: () => {
              this.ngOnInit();
              // Show success dialog - no callback needed
              this.dialogService.showRobustDialog(
                'Success',
                `User ${username} deleted successfully!`,
                'success'
              );
            },
            error: (err) => {
              console.error(`Failed to delete user ${username}:`, err);
              // Show error dialog - no callback needed
              this.dialogService.showRobustDialog(
                'Deletion Failed',
                `Failed to delete user ${username}. Please try again.`,
                'error'
              );
            }
          });
        }
      }
    );
  }

  onEditUser(username: string): void {
    this.router.navigate(['/account/edit', username]);
  }

  onResetUser(user: User): void {
    // Use the new robust dialog method for confirmation
    this.dialogService.showRobustDialog(
      'Confirm Password Reset',
      `Are you sure you want to reset the password for ${user.username}?`,
      'confirm',
      (confirmed) => {
        if (confirmed) {
          this.http.put(`/api/v1/auth/reset/${user.id}`, {}, { responseType: 'text'}).subscribe({
            next: (response) => {
              console.log('Password reset response:', response);
              // Show success dialog - no callback needed
              this.dialogService.showRobustDialog(
                'Success',
                'Successfully reset password',
                'success'
              );
            },
            error: (err) => {
              console.error(`Failed to reset password.`, err);
              // Show error dialog - no callback needed
              this.dialogService.showRobustDialog(
                'Reset Failed',
                'Failed to reset password',
                'error'
              );
            }
          });
        }
      }
    );
  }
}