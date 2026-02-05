import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ScaleQuestion } from '../../../../../models/question.model';

@Component({
  selector: 'app-scale-question',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scale-question.component.html',
  styleUrl: './scale-question.component.scss'
})
export class ScaleQuestionComponent {
  @Input() data!: ScaleQuestion;
  @Output() dataChange = new EventEmitter<ScaleQuestion>();
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