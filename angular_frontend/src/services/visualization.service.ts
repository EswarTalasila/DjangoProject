import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface VisualizationFilters {
  studentId?: number | null;
  courseId?: number | null;
  category?: string | null;
  assessmentId?: number | null;
  teacherId?: number | null;
  isMoodMeter?: boolean;
}

export interface VisualizationSubmission {
  id: number;
  assignmentId: number;
  studentId?: number;
  teacherId?: number;
  submittedAt: string;
  score?: number;
  status: string;
  answers: any[];
  anonymousUsername?: string;
  assessmentTitle?: string;
  assessmentCategory?: string;
  courseId?: number;
  courseName?: string;
}

export interface ProcessedChartData {
  scoreTrends: any[];
  scoreDistribution: any[];
  moodMeterData: MoodMeterPoint[];
  statistics: {
    mean: number;
    median: number;
    stdDev: number;
    count: number;
  };
}

export interface MoodMeterPoint {
  name: string;
  energy: number;
  pleasantness: number;
  count: number;
}

export interface DataPoint {
  name: string;
  value: number;
}


@Injectable({
  providedIn: 'root'
})
export class VisualizationService {
  private baseUrl = '/api/v1';

  constructor(private http: HttpClient) {}

  /**
   * Fetches visualization data from the backend
   */
  getVisualizationData(filters: VisualizationFilters): Observable<VisualizationSubmission[]> {
    return this.http.post<VisualizationSubmission[]>(
      `${this.baseUrl}/visualization`,
      filters,
      { withCredentials: true }
    );
  }

  /**
   * Process raw submission data for charts
   */
  processDataForCharts(submissions: VisualizationSubmission[]): ProcessedChartData {
    if (!submissions || submissions.length === 0) {
      return {
        scoreTrends: [],
        scoreDistribution: [],
        moodMeterData: [],
        statistics: { mean: 0, median: 0, stdDev: 0, count: 0 }
      };
    }

    return {
      scoreTrends: this.processScoreTrends(submissions),
      scoreDistribution: this.processScoreDistribution(submissions),
      moodMeterData: this.processMoodMeterData(submissions),
      statistics: this.calculateStatistics(submissions)
    };
  }

  /**
   * Process score trends over time
   */
  private processScoreTrends(submissions: VisualizationSubmission[]): any[] {
    const sorted = [...submissions]
      .filter(s => s.score !== null && s.score !== undefined)
      .sort((a, b) => new Date(a.submittedAt).getTime() - new Date(b.submittedAt).getTime());

    return [{
      name: 'Scores',
      series: sorted.map((s, idx) => ({
        name: new Date(s.submittedAt).toLocaleDateString(),
        value: s.score,
        extra: {
          submission: idx + 1,
          student: s.anonymousUsername || 'Anonymous'
        }
      }))
    }];
  }

  /**
   * Process score distribution for histogram
   */
  private processScoreDistribution(submissions: VisualizationSubmission[]): any[] {
    const scores = submissions
      .filter(s => s.score !== null && s.score !== undefined)
      .map(s => s.score!);

    if (scores.length === 0) return [];

    const bins: { [key: string]: number } = {};
    for (let i = 0; i < 10; i++) {
      const label = `${i * 10}-${(i + 1) * 10}`;
      bins[label] = 0;
    }

    scores.forEach(score => {
      const binIndex = Math.min(Math.floor(score / 10), 9);
      const label = `${binIndex * 10}-${(binIndex + 1) * 10}`;
      bins[label]++;
    });

    return Object.entries(bins).map(([name, value]) => ({ name, value }));
  }

  /**
   * Process mood meter data for heatmap
   */
private processMoodMeterData(submissions: VisualizationSubmission[]): MoodMeterPoint[] {
  const moodCounts = new Map<string, MoodMeterPoint>();

  submissions.forEach(submission => {
    submission.answers.forEach(answer => {
      if (answer.type === 'MOOD_METER' && answer.data) {
        const { row, col } = answer.data;
        if (row === undefined || col === undefined) return;

        const key = `${row},${col}`;
        if (!moodCounts.has(key)) {
          moodCounts.set(key, {
            name: `(${row}, ${col})`,
            energy: row,
            pleasantness: col,
            count: 0
          });
        }
        moodCounts.get(key)!.count++;
      }
    });
  });

  return Array.from(moodCounts.values());
}

  /**
   * Calculate statistical measures
   */
  private calculateStatistics(submissions: VisualizationSubmission[]): any {
    const scores = submissions
      .filter(s => s.score !== null && s.score !== undefined)
      .map(s => s.score!);

    if (scores.length === 0) {
      return { mean: 0, median: 0, stdDev: 0, count: 0 };
    }

    const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
    
    const sorted = [...scores].sort((a, b) => a - b);
    const median = scores.length % 2 === 0
      ? (sorted[scores.length / 2 - 1] + sorted[scores.length / 2]) / 2
      : sorted[Math.floor(scores.length / 2)];

    const variance = scores.reduce((sum, score) => sum + Math.pow(score - mean, 2), 0) / scores.length;
    const stdDev = Math.sqrt(variance);

    return {
      mean: Math.round(mean * 100) / 100,
      median: Math.round(median * 100) / 100,
      stdDev: Math.round(stdDev * 100) / 100,
      count: scores.length
    };
  }

  /**
   * Check if data meets minimum sample size
   */
  checkMinimumSampleSize(count: number, minSize: number = 5): boolean {
    return count >= minSize;
  }
}