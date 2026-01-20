import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { User, UserService } from '../../../../services/user.service';
import { DialogService } from '../../../../services/dialog.service';

interface Role {
  id: number;
  name: string;
}

interface UserDto {
  id: number;
  name?: string;
  username: string;
  roles: Role[];
}

@Component({
  selector: 'app-account-edit',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './account.edit.component.html',
  styleUrls: ['./account.edit.component.scss']
})
export class AccountEditComponent {

  roleValue: string = 'admin';
  firstName: string = '';
  lastName: string = '';
  email: string = '';
  password: string = '';
  confirmPassword: string = '';
  previousEmail: string = '';
  id: number | null = null;

  private isEditMode = false;
  private usernameToEdit: string | null = null;

  constructor(
    private router: Router, 
    private http: HttpClient, 
    private route: ActivatedRoute, 
    private dialogService: DialogService,
    private userService: UserService
  ) {}

  //Initialize and load user from list of users
  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const username = params.get('username');
      if (username) {
        this.isEditMode = true;
        this.usernameToEdit = username;
        this.loadUserFromList(username);
      }
    });
  }

  // Loads a specific user from a list of users
  loadUserFromList(username: string) {
    this.http.get<User[]>('/api/v1/auth/teachers-admins').subscribe({
      next: (users) => {
        const user = users.find(u => u.username === username);
        if (!user) {
          // Use the new robust dialog method
          this.dialogService.showRobustDialog(
            'User Not Found', 
            'User not found', 
            'error', 
            () => this.router.navigate(['/account'])
          );
          return;
        }
        // Map user data to form fields
        const [first, last] = (user.name || '').split(' ');
        if(user.id) {
          this.id = user.id;
        }
        this.firstName = first || '';
        this.lastName = last || '';
        this.email = user.username || '';
        this.previousEmail = user.username || '';
        this.roleValue = user.role === 'ROLE_ADMIN' ? 'admin' : 'teacher';
      },
      error: (err) => {
        console.error('Failed to fetch users:', err);
        // Use the new robust dialog method
        this.dialogService.showRobustDialog(
          'Load Failed', 
          'Failed to load user data', 
          'error', 
          () => this.router.navigate(['/account'])
        );
      }
    });
  }

  // Changes are set to API endpoint
  onSubmit(event: Event) {
    let edit: User = {
      firstName: this.firstName,
      lastName: this.lastName,
      name: this.firstName + " " + this.lastName,
      username: this.email,
      password: null
    };
    console.log(edit);

    if (this.roleValue.toLowerCase() === 'admin') {
      edit.role = 'ROLE_ADMIN' ;
    } else if (this.roleValue.toLowerCase() === 'teacher') {
      edit.role = 'ROLE_TEACHER';
    } else {
      // Use the new robust dialog method
      this.dialogService.showRobustDialog('Invalid Role', 'Invalid role selected', 'error');
      return;
    }
    if(this.id) {
      this.userService.editUser(edit, this.id).subscribe({
        next: (response) => {
            // Use the new robust dialog method
            this.dialogService.showRobustDialog(
              'Success', 
              response, 
              'success', 
              () => this.router.navigate(['/account'])
            );
        },
        error: (error) => {
          console.error('Error editing user:', error);
          console.log('Error details:', error);

          // Use the new robust dialog method
          this.dialogService.showRobustDialog(
            'Edit Failed', 
            'Failed to edit user. Please try again.', 
            'error'
          );
        }
      });
    }
  }
}