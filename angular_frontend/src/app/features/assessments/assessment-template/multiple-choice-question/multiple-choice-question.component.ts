import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MultipleChoiceQuestion } from '../../../../../models/question.model';

@Component({
  selector: 'app-multiple-choice-question',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './multiple-choice-question.component.html',
  styleUrl: './multiple-choice-question.component.scss',
})
export class MultipleChoiceQuestionComponent {
  @Input() data!: MultipleChoiceQuestion;
  @Output() dataChange = new EventEmitter<MultipleChoiceQuestion>();
  @Output() delete = new EventEmitter<void>();

  onDataChange() {
    this.dataChange.emit(this.data);
  }

  addChoice() {
    if (!this.data.choices) {
      this.data.choices = [];
    }
    this.data.choices.push({ prompt: '', score: 0 });
    this.onDataChange();
  }

  removeChoice(index: number) {
    this.data.choices.splice(index, 1);
    this.data.correctAnswers = this.data.correctAnswers.filter(
      (i) => i !== index
    );
    this.data.correctAnswers = this.data.correctAnswers.map((i) =>
      i > index ? i - 1 : i
    );
    this.onDataChange();
  }

  toggleCorrectAnswer(index: number) {
    if (!this.data.correctAnswers) {
      this.data.correctAnswers = [];
    }

    const correctIndex = this.data.correctAnswers.indexOf(index);
    if (correctIndex > -1) {
      this.data.correctAnswers.splice(correctIndex, 1);
    } else {
      if (!this.data.selectAll) {
        this.data.correctAnswers = [index];
      } else {
        this.data.correctAnswers.push(index);
      }
    }
    this.onDataChange();
  }

  isCorrect(index: number): boolean {
    return this.data.correctAnswers?.includes(index) || false;
  }

  onImageSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.data.image = e.target.result;
        this.onDataChange();
      };
      reader.readAsDataURL(file);
    }
  }

  onDelete() {
    this.delete.emit();
  }
  
  autoExpand(event: Event) {
      const textarea = event.target as HTMLTextAreaElement;
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
      
      const maxHeight = 200;
      if (textarea.scrollHeight > maxHeight) {
        textarea.style.height = maxHeight + 'px';
        textarea.style.overflowY = 'auto';
      } else {
        textarea.style.overflowY = 'hidden';
      }
    }
}
