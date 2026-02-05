import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { AccountEditComponent } from './account.edit.component';

describe('AccountEditComponent', () => {
  let component: AccountEditComponent;
  let fixture: ComponentFixture<AccountEditComponent>;

  beforeEach(async () => {
    const mockUserData = [
      {
        id: 1,
        name: 'Test User',
        username: 'testuser',
        roles: [{ id: 1, name: 'ROLE_ADMIN' }],
      },
    ];

    const activatedRouteStub = {
      paramMap: {
        subscribe: (fn: (params: any) => void) =>
          fn({
            get: (param: string) => (param === 'username' ? 'testuser' : null),
          }),
      },
    };

    const httpClientStub = {
      get: () => of(mockUserData),
    };

    await TestBed.configureTestingModule({
      imports: [AccountEditComponent],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteStub },
        { provide: HttpClient, useValue: httpClientStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccountEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
