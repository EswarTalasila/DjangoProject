import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ShortAnswerQuestion } from '../../../../../models/question.model';

@Component({
  selector: 'app-short-answer-question',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './short-answer-question.component.html',
  styleUrl: './short-answer-question.component.scss'
})
export class ShortAnswerQuestionComponent {
  @Input() data!: ShortAnswerQuestion;
  @Output() dataChange = new EventEmitter<ShortAnswerQuestion>();
  @Output() delete = new EventEmitter<void>();

  onDataChange() {
    this.dataChange.emit(this.data);
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