import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScaleQuestionComponent } from './scale-question.component';

describe('ScaleQuestionComponent', () => {
  let component: ScaleQuestionComponent;
  let fixture: ComponentFixture<ScaleQuestionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScaleQuestionComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ScaleQuestionComponent);
    component = fixture.componentInstance;
    component.data = {
      id: '1',
      maxPoints: 10,
      autoGradable: true,
      type: 'scale',
      prompt: 'Sample question',
      min: 1,
      max: 5,
    };
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
