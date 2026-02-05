import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UserService } from '../../../services/user.service';
import { Subscription } from 'rxjs';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent {
  userRole: any;
  userId: any;
  private roleSubscription: Subscription | null = null;
  private idSubscription: Subscription | null = null;

  constructor(private userService: UserService){}
  
  ngOnInit(): void {
    // Subscribe to the userRole observable to get updates
    this.roleSubscription = this.userService.getUserRole().subscribe((role) => {
      this.userRole = role;
    });

    this.idSubscription = this.userService.getUserId().subscribe((id) => {
      this.userId = id;
    });
  }

  ngOnDestroy(): void {
    // Unsubscribe to avoid memory leaks
    if (this.roleSubscription) {
      this.roleSubscription.unsubscribe();
    }

    if (this.idSubscription) {
      this.idSubscription.unsubscribe();
    }
  }
}