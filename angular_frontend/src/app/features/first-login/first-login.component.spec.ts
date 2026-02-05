import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FirstLoginComponent } from './first-login.component';
import { ActivatedRoute } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('FirstLoginComponent', () => {
  let component: FirstLoginComponent;
  let fixture: ComponentFixture<FirstLoginComponent>;

  beforeEach(async () => {
    const activatedRouteStub = ({
      snapshot: {
        params: { userId: 1 }
      }
    }) as unknown as Partial<ActivatedRoute>;

    await TestBed.configureTestingModule({
      imports: [
        FirstLoginComponent
      ],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteStub },
        provideHttpClient(), provideHttpClientTesting()
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(FirstLoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
