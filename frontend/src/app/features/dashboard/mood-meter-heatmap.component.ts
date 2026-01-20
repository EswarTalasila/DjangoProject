import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MoodMeterPoint } from '../../../services/visualization.service';

@Component({
  selector: 'app-mood-meter-heatmap',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="mood-meter-container">
      <div class="mood-meter">
        <div class="quadrant high-energy low-pleasantness">
          <div class="title">High Energy / Low Pleasantness</div>
          <div class="mood-grid">
            <div
              *ngFor="let mood of moods.highEnergyLowPleasantness"
              class="mood"
              [class.has-responses]="getMoodCount(mood.name) > 0"
              [style.grid-row]="(mood.row % 5) + 1"
              [style.grid-column]="(mood.col % 5) + 1"
              [style.opacity]="getMoodOpacity(mood.name)"
              [style.font-weight]="getMoodCount(mood.name) > 0 ? '700' : '400'"
              [title]="getMoodTooltip(mood.name)"
            >
              {{ mood.name }}
              <span class="count-badge" *ngIf="getMoodCount(mood.name) > 0">
                {{ getMoodCount(mood.name) }}
              </span>
            </div>
          </div>
        </div>

        <div class="quadrant high-energy high-pleasantness">
          <div class="title">High Energy / High Pleasantness</div>
          <div class="mood-grid">
            <div
              *ngFor="let mood of moods.highEnergyHighPleasantness"
              class="mood"
              [class.has-responses]="getMoodCount(mood.name) > 0"
              [style.grid-row]="(mood.row % 5) + 1"
              [style.grid-column]="(mood.col % 5) + 1"
              [style.opacity]="getMoodOpacity(mood.name)"
              [style.font-weight]="getMoodCount(mood.name) > 0 ? '700' : '400'"
              [title]="getMoodTooltip(mood.name)"
            >
              {{ mood.name }}
              <span class="count-badge" *ngIf="getMoodCount(mood.name) > 0">
                {{ getMoodCount(mood.name) }}
              </span>
            </div>
          </div>
        </div>

        <div class="quadrant low-energy low-pleasantness">
          <div class="title">Low Energy / Low Pleasantness</div>
          <div class="mood-grid">
            <div
              *ngFor="let mood of moods.lowEnergyLowPleasantness"
              class="mood"
              [class.has-responses]="getMoodCount(mood.name) > 0"
              [style.grid-row]="(mood.row % 5) + 1"
              [style.grid-column]="(mood.col % 5) + 1"
              [style.opacity]="getMoodOpacity(mood.name)"
              [style.font-weight]="getMoodCount(mood.name) > 0 ? '700' : '400'"
              [title]="getMoodTooltip(mood.name)"
            >
              {{ mood.name }}
              <span class="count-badge" *ngIf="getMoodCount(mood.name) > 0">
                {{ getMoodCount(mood.name) }}
              </span>
            </div>
          </div>
        </div>
        <div class="quadrant low-energy high-pleasantness">
          <div class="title">Low Energy / High Pleasantness</div>
          <div class="mood-grid">
            <div
              *ngFor="let mood of moods.lowEnergyHighPleasantness"
              class="mood"
              [class.has-responses]="getMoodCount(mood.name) > 0"
              [style.grid-row]="(mood.row % 5) + 1"
              [style.grid-column]="(mood.col % 5) + 1"
              [style.opacity]="getMoodOpacity(mood.name)"
              [style.font-weight]="getMoodCount(mood.name) > 0 ? '700' : '400'"
              [title]="getMoodTooltip(mood.name)"
            >
              {{ mood.name }}
              <span class="count-badge" *ngIf="getMoodCount(mood.name) > 0">
                {{ getMoodCount(mood.name) }}
              </span>
            </div>
          </div>
        </div>
        <div class="axis x-axis">Low pleasantness</div>
        <div class="axis x-axis high">High pleasantness</div>
        <div class="axis y-axis">Low energy</div>
        <div class="axis y-axis high">High energy</div>
      </div>

      <p class="attribution">
        This information was adapted from Soma & Soul with permission from Kim
        Jeffs.
      </p>

      <div class="summary-stats">
        <div class="stat-item">
          <span class="stat-label">Total Responses:</span>
          <span class="stat-value">{{ totalResponses }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Most Selected Mood:</span>
          <span class="stat-value">{{ mostSelectedMood }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Most Common Quadrant:</span>
          <span class="stat-value">{{ mostCommonQuadrant }}</span>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        font-family: Arial, Helvetica, sans-serif;
        max-width: 100%;
        padding: 1rem;
        box-sizing: border-box;
        color: var(--text-color);
      }

      h3 {
        margin: 0 0 0.5rem 0;
        color: var(--text-color);
        font-size: 1.25rem;
      }

      p {
        text-align: center;
        color: #6c757d;
        font-size: 0.875em;
      }

      .mood-meter-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100%;
        box-sizing: border-box;
      }

      .mood-meter {
        display: grid;
        grid-template-columns: 1fr 1fr;
        grid-template-rows: 1fr 1fr;
        width: 1000px;
        height: 700px;
        position: relative;
        margin-bottom: 25px;
      }

      .mood-meter::before,
      .mood-meter::after {
        content: '';
        position: absolute;
        background-color: black;
        z-index: 1;
      }

      .mood-meter::before {
        width: 4px;
        height: 100%;
        left: 50%;
        transform: translateX(-50%);
      }

      .mood-meter::after {
        width: 100%;
        height: 4px;
        top: 50%;
        transform: translateY(-50%);
      }

      .quadrant {
        display: flex;
        flex-direction: column;
        padding: 25px;
        overflow-y: auto;
        border-radius: 20px;
      }

      .title {
        text-align: center;
        font-weight: bold;
        margin-bottom: 10px;
        color: var(--text-color);
      }

      .high-energy.low-pleasantness {
        background-color: #faf2fb;
      }

      .high-energy.high-pleasantness {
        background-color: #eef4dd;
      }

      .low-energy.low-pleasantness {
        background-color: #f8f5f0;
      }

      .low-energy.high-pleasantness {
        background-color: #f4faff;
      }

      .mood-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        grid-template-rows: repeat(5, 1fr);
        gap: 4px;
        flex: 1;
        padding: 8px;
        min-height: 250px;
      }

      .mood {
        background-color: rgba(255, 255, 255, 0.4);
        border-radius: 4px;
        padding: 2px 4px;
        cursor: default;
        transition: all 0.3s ease;
        font-size: 0.75rem;
        white-space: normal;
        word-wrap: break-word;
        overflow-wrap: break-word;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        position: relative;
        color: var(--text-color);
        border: 2px solid transparent;
        min-height: 35px;
        line-height: 1.1;
        hyphens: auto;
      }

      .mood.has-responses {
        background-color: black;
        color: white;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        transform: scale(1.05);
        border-color: var(--button-color);
      }

      .mood:hover {
        transform: scale(1.1);
        z-index: 10;
      }

      .count-badge {
        position: absolute;
        top: -8px;
        right: -8px;
        background-color: var(--button-color);
        color: var(--button-text-color);
        border-radius: 50%;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        z-index: 2;
      }

      .axis {
        position: absolute;
        font-weight: bold;
        color: black;
        font-size: 1rem;
        z-index: 2;
      }

      .x-axis {
        bottom: -35px;
        left: 15px;
      }

      .x-axis.high {
        right: 15px;
        left: auto;
      }

      .y-axis {
        left: -55px;
        bottom: 10px;
        writing-mode: vertical-rl;
        transform: rotate(180deg);
      }

      .y-axis.high {
        bottom: auto;
        top: 10px;
        left: -55px;
        writing-mode: vertical-lr;
        transform: rotate(180deg);
      }

      .attribution {
        font-size: 0.75rem;
        text-align: center;
        color: var(--text-color);
        opacity: 0.7;
        margin-top: 1rem;
      }

      .summary-stats {
        display: flex;
        justify-content: space-around;
        gap: 2rem;
        padding: 1.5rem;
        background: var(--primary-color);
        border: 2px solid rgba(0, 0, 0, 0.1);
        border-radius: 8px;
        margin-top: 1rem;
        width: 100%;
        max-width: 1000px;
      }

      .stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
      }

      .stat-label {
        font-size: 0.875rem;
        color: var(--text-color);
        opacity: 0.8;
        font-weight: 500;
        text-align: center;
      }

      .stat-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--button-color);
        text-align: center;
      }

      @media (max-width: 1100px) {
        .mood-meter {
          width: 90vw;
          height: calc(90vw * 0.7);
        }
      }

      @media (max-width: 768px) {
        .mood-meter {
          width: 95vw;
          height: calc(95vw * 0.7);
        }

        .mood {
          font-size: 0.7rem;
          padding: 2px;
        }

        .summary-stats {
          flex-direction: column;
          gap: 1rem;
        }
      }
    `,
  ],
})
export class MoodMeterHeatmapComponent implements OnChanges {
  @Input() moodData: MoodMeterPoint[] = [];

  moods = {
    highEnergyLowPleasantness: [
      { name: 'Enraged', row: 0, col: 0 },
      { name: 'Panicked', row: 0, col: 1 },
      { name: 'Stressed', row: 0, col: 2 },
      { name: 'Jittery', row: 0, col: 3 },
      { name: 'Shocked', row: 0, col: 4 },
      { name: 'Livid', row: 1, col: 0 },
      { name: 'Furious', row: 1, col: 1 },
      { name: 'Frustrated', row: 1, col: 2 },
      { name: 'Tense', row: 1, col: 3 },
      { name: 'Stunned', row: 1, col: 4 },
      { name: 'Fuming', row: 2, col: 0 },
      { name: 'Frightened', row: 2, col: 1 },
      { name: 'Angry', row: 2, col: 2 },
      { name: 'Nervous', row: 2, col: 3 },
      { name: 'Restless', row: 2, col: 4 },
      { name: 'Anxious', row: 3, col: 0 },
      { name: 'Apprehensive', row: 3, col: 1 },
      { name: 'Worried', row: 3, col: 2 },
      { name: 'Irritated', row: 3, col: 3 },
      { name: 'Annoyed', row: 3, col: 4 },
      { name: 'Repulsed', row: 4, col: 0 },
      { name: 'Troubled', row: 4, col: 1 },
      { name: 'Concerned', row: 4, col: 2 },
      { name: 'Uneasy', row: 4, col: 3 },
      { name: 'Peeved', row: 4, col: 4 },
    ],
    highEnergyHighPleasantness: [
      { name: 'Surprised', row: 0, col: 5 },
      { name: 'Upbeat', row: 0, col: 6 },
      { name: 'Festive', row: 0, col: 7 },
      { name: 'Exhilarated', row: 0, col: 8 },
      { name: 'Ecstatic', row: 0, col: 9 },
      { name: 'Hyper', row: 1, col: 5 },
      { name: 'Cheerful', row: 1, col: 6 },
      { name: 'Motivated', row: 1, col: 7 },
      { name: 'Inspired', row: 1, col: 8 },
      { name: 'Elated', row: 1, col: 9 },
      { name: 'Energized', row: 2, col: 5 },
      { name: 'Lively', row: 2, col: 6 },
      { name: 'Excited', row: 2, col: 7 },
      { name: 'Optimistic', row: 2, col: 8 },
      { name: 'Enthusiastic', row: 2, col: 9 },
      { name: 'Pleased', row: 3, col: 5 },
      { name: 'Focused', row: 3, col: 6 },
      { name: 'Happy', row: 3, col: 7 },
      { name: 'Proud', row: 3, col: 8 },
      { name: 'Thrilled', row: 3, col: 9 },
      { name: 'Pleasant', row: 4, col: 5 },
      { name: 'Joyful', row: 4, col: 6 },
      { name: 'Hopeful', row: 4, col: 7 },
      { name: 'Playful', row: 4, col: 8 },
      { name: 'Blissful', row: 4, col: 9 },
    ],
    lowEnergyLowPleasantness: [
      { name: 'Disgusted', row: 5, col: 0 },
      { name: 'Glum', row: 5, col: 1 },
      { name: 'Disappointed', row: 5, col: 2 },
      { name: 'Down', row: 5, col: 3 },
      { name: 'Apathetic', row: 5, col: 4 },
      { name: 'Pessimistic', row: 6, col: 0 },
      { name: 'Morose', row: 6, col: 1 },
      { name: 'Discouraged', row: 6, col: 2 },
      { name: 'Sad', row: 6, col: 3 },
      { name: 'Bored', row: 6, col: 4 },
      { name: 'Alienated', row: 7, col: 0 },
      { name: 'Miserable', row: 7, col: 1 },
      { name: 'Lonely', row: 7, col: 2 },
      { name: 'Disheartened', row: 7, col: 3 },
      { name: 'Tired', row: 7, col: 4 },
      { name: 'Despondent', row: 8, col: 0 },
      { name: 'Depressed', row: 8, col: 1 },
      { name: 'Sullen', row: 8, col: 2 },
      { name: 'Exhausted', row: 8, col: 3 },
      { name: 'Fatigued', row: 8, col: 4 },
      { name: 'Despairing', row: 9, col: 0 },
      { name: 'Hopeless', row: 9, col: 1 },
      { name: 'Desolate', row: 9, col: 2 },
      { name: 'Spent', row: 9, col: 3 },
      { name: 'Drained', row: 9, col: 4 },
    ],
    lowEnergyHighPleasantness: [
      { name: 'Eddied', row: 5, col: 5 },
      { name: 'Easy-Going', row: 5, col: 6 },
      { name: 'Content', row: 5, col: 7 },
      { name: 'Loving', row: 5, col: 8 },
      { name: 'Fulfilled', row: 5, col: 9 },
      { name: 'Calm', row: 6, col: 5 },
      { name: 'Secure', row: 6, col: 6 },
      { name: 'Satisfied', row: 6, col: 7 },
      { name: 'Grateful', row: 6, col: 8 },
      { name: 'Touched', row: 6, col: 9 },
      { name: 'Relaxed', row: 7, col: 5 },
      { name: 'Chill', row: 7, col: 6 },
      { name: 'Restful', row: 7, col: 7 },
      { name: 'Blessed', row: 7, col: 8 },
      { name: 'Balanced', row: 7, col: 9 },
      { name: 'Mellow', row: 8, col: 5 },
      { name: 'Thoughtful', row: 8, col: 6 },
      { name: 'Peaceful', row: 8, col: 7 },
      { name: 'Comfortable', row: 8, col: 8 },
      { name: 'Carefree', row: 8, col: 9 },
      { name: 'Sleepy', row: 9, col: 5 },
      { name: 'Complacent', row: 9, col: 6 },
      { name: 'Tranquil', row: 9, col: 7 },
      { name: 'Cozy', row: 9, col: 8 },
      { name: 'Serene', row: 9, col: 9 },
    ],
  };

  moodCounts = new Map<string, number>();
  totalResponses = 0;
  mostSelectedMood = 'None';
  mostCommonQuadrant = 'N/A';
  maxCount = 0;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['moodData']) {
      this.processData();
    }
  }

  private processData(): void {
    this.moodCounts.clear();
    this.totalResponses = 0;

    this.moodData.forEach((point) => {
      const moodName = this.getMoodNameByPosition(
        point.energy,
        point.pleasantness
      );
      if (moodName) {
        this.moodCounts.set(moodName, point.count);
        this.totalResponses += point.count;
        this.maxCount = Math.max(this.maxCount, point.count);
      }
    });

    this.calculateStats();
  }

  private getMoodNameByPosition(row: number, col: number): string | null {
    const allMoods = [
      ...this.moods.highEnergyLowPleasantness,
      ...this.moods.highEnergyHighPleasantness,
      ...this.moods.lowEnergyLowPleasantness,
      ...this.moods.lowEnergyHighPleasantness,
    ];

    const mood = allMoods.find((m) => m.row === row && m.col === col);
    return mood ? mood.name : null;
  }

  private calculateStats(): void {
    let maxCount = 0;
    let topMood = 'None';
    this.moodCounts.forEach((count, mood) => {
      if (count > maxCount) {
        maxCount = count;
        topMood = mood;
      }
    });
    this.mostSelectedMood = topMood;

    const quadrantCounts = {
      'High Energy / Low Pleasantness': 0,
      'High Energy / High Pleasantness': 0,
      'Low Energy / Low Pleasantness': 0,
      'Low Energy / High Pleasantness': 0,
    };

    this.moods.highEnergyLowPleasantness.forEach((m) => {
      quadrantCounts['High Energy / Low Pleasantness'] +=
        this.moodCounts.get(m.name) || 0;
    });
    this.moods.highEnergyHighPleasantness.forEach((m) => {
      quadrantCounts['High Energy / High Pleasantness'] +=
        this.moodCounts.get(m.name) || 0;
    });
    this.moods.lowEnergyLowPleasantness.forEach((m) => {
      quadrantCounts['Low Energy / Low Pleasantness'] +=
        this.moodCounts.get(m.name) || 0;
    });
    this.moods.lowEnergyHighPleasantness.forEach((m) => {
      quadrantCounts['Low Energy / High Pleasantness'] +=
        this.moodCounts.get(m.name) || 0;
    });

    let maxQuadrantCount = 0;
    let topQuadrant = 'N/A';
    Object.entries(quadrantCounts).forEach(([name, count]) => {
      if (count > maxQuadrantCount) {
        maxQuadrantCount = count;
        topQuadrant = name;
      }
    });
    this.mostCommonQuadrant = maxQuadrantCount > 0 ? topQuadrant : 'N/A';
  }

  getMoodCount(moodName: string): number {
    return this.moodCounts.get(moodName) || 0;
  }

  getMoodOpacity(moodName: string): number {
    const count = this.getMoodCount(moodName);
    if (count === 0) return 0.4;
    return 1.0;
  }

  getMoodTooltip(moodName: string): string {
    const count = this.getMoodCount(moodName);
    return count > 0
      ? `${moodName}: ${count} response${count !== 1 ? 's' : ''}`
      : moodName;
  }
}
