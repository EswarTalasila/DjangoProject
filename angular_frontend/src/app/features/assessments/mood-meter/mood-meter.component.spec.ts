import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MoodMeterComponent } from './mood-meter.component';

describe('MoodMeterComponent', () => {
  let component: MoodMeterComponent;
  let fixture: ComponentFixture<MoodMeterComponent>;

  beforeEach(async () => {
    const activatedRouteStub = {
      snapshot: {
        paramMap: convertToParamMap({ studentId: '1' }),
      },
    } as Partial<ActivatedRoute>;
    await TestBed.configureTestingModule({
      imports: [MoodMeterComponent],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteStub },
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MoodMeterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
