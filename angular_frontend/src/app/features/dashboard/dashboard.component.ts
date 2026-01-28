import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { NgxEchartsDirective } from 'ngx-echarts';
import { BarSeriesOption, EChartsOption, LineSeriesOption } from 'echarts';
import { UserService } from '../../../services/user.service';
import { ExportService } from '../../../services/export-data.service';
import {
  VisualizationService,
  VisualizationFilters,
  ProcessedChartData,
  VisualizationSubmission,
  DataPoint,
} from '../../../services/visualization.service';
import { FilterPanelComponent } from './filters/filter-panel.component';
import { MoodMeterHeatmapComponent } from './mood-meter-heatmap.component';
import { DialogService } from '../../../services/dialog.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    NgxEchartsDirective,
    FilterPanelComponent,
    MoodMeterHeatmapComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})

export class DashboardComponent implements OnInit, OnDestroy {
  userRole: string = '';
  private roleSubscription: Subscription | null = null;

  chartData: ProcessedChartData | null = null;
  cleanedData: ProcessedChartData | null = null;
  currentFilters: VisualizationFilters = {};
  showInsufficientDataWarning = false;

  private chartPalette = ['#4361ee', '#3a0ca3', '#7209b7', '#f72585'];

  lineOptions: EChartsOption = {};
  barOptions: EChartsOption = {};

  view: [number, number] = [700, 400];
  showXAxis = true;
  showYAxis = true;
  gradient = false;
  showLegend = true;
  showXAxisLabel = true;
  xAxisLabel = 'Date';
  showYAxisLabel = true;
  yAxisLabel = 'Score';
  timeline = true;

  distributionView: [number, number] = [700, 300];
  distributionXAxisLabel = 'Score Range';
  distributionYAxisLabel = 'Frequency';
  rawSubmissions: VisualizationSubmission[] = [];
  isExporting = false;

  constructor(
    private userService: UserService,
    private vizService: VisualizationService,
    private exportService: ExportService,
    private dialogService: DialogService,
  ) {}

  ngOnInit(): void {
    this.roleSubscription = this.userService.getUserRole().subscribe((role) => {
      this.userRole = role || '';
    });

    // MOCK DATA - DELETE WHEN FUNCTIONALITY IS FINALIZED
    // this.testWithMockData(this.generateCompleteMockData());
    // this.cleanData();
    
  }

  ngOnDestroy(): void {
    if (this.roleSubscription) {
      this.roleSubscription.unsubscribe();
    }
  }

  cleanData(): void {
    if (!this.chartData?.scoreTrends) {
      console.error("No scoreTrends data available.");
      return;
    }

    const cleanedData: ProcessedChartData = { ...this.chartData };

    cleanedData.scoreTrends = cleanedData.scoreTrends.map((series) => {
      const name = series.name;
      
      const dataMap = new Map<string, { sum: number; count: number }>();

      series.series.forEach((point: DataPoint) => {
        if (dataMap.has(point.name)) {
          const data = dataMap.get(point.name)!;
          data.sum += point.value;
          data.count += 1;
        } else {
          dataMap.set(point.name, { sum: point.value, count: 1 });
        }
      });

      const cleanedSeries = Array.from(dataMap.entries()).map(([name, data]) => ({
        name,
        value: data.sum / data.count,
      }));

      return {
        name,
        series: cleanedSeries,
      };
    });

    this.cleanedData = cleanedData;
    this.updateChartOptions();

    console.log('Cleaned data:', this.cleanedData);
  }


  onFiltersChanged(filters: VisualizationFilters): void {
    this.currentFilters = filters;
    this.loadVisualizationData();
  }

  private loadVisualizationData(): void {
    this.showInsufficientDataWarning = false;

    this.vizService.getVisualizationData(this.currentFilters).subscribe({
      next: (submissions) => {
        this.rawSubmissions = submissions;
        this.chartData = this.vizService.processDataForCharts(submissions);

        if (
          !this.vizService.checkMinimumSampleSize(
            this.chartData.statistics.count
          )
        ) {
          this.showInsufficientDataWarning = true;
        }

        this.cleanData();
      },
      error: (err) => {
        console.error('Visualization error:', err);
      },
    });
  }

  get hasData(): boolean {
    return !!this.chartData && this.chartData.statistics.count > 0;
  }

  get showMoodMeterHeatmap(): boolean {
    return (
      !!this.currentFilters.isMoodMeter &&
      !!this.chartData &&
      this.chartData.moodMeterData.length > 0
    );
  }

  get showStatisticalCharts(): boolean {
    return (
      this.hasData &&
      this.vizService.checkMinimumSampleSize(this.chartData!.statistics.count)
    );
  }

  onSelect(event: any): void {
    console.log('Chart item selected:', event);
  }

  exportAsCSV(): void {
    if (!this.chartData || !this.rawSubmissions.length) {
      this.dialogService.showRobustDialog('No Data', 'No data available to export', 'error');
      return;
    }

    this.exportService.exportToCSV(
      this.rawSubmissions,
      this.chartData,
      this.currentFilters
    );
  }

  async exportAsPDF(): Promise<void> {
    if (!this.chartData) {
      this.dialogService.showRobustDialog('No Data', 'No data available to export', 'error');
      return;
    }

    this.isExporting = true;
    try {
      await this.exportService.exportToPDF(this.chartData, this.currentFilters);
    } finally {
      this.isExporting = false;
    }
  }

  get canExport(): boolean {
    return this.hasData && this.rawSubmissions.length > 0;
  }

  get isAdmin(): boolean {
    return this.userRole === 'ADMIN';
  }

  get isTeacher(): boolean {
    return this.userRole === 'TEACHER';
  }

  private updateChartOptions(): void {
    if (!this.cleanedData || !this.chartData) {
      this.lineOptions = {};
      this.barOptions = {};
      return;
    }

    const lineSeries = this.cleanedData.scoreTrends ?? [];
    const lineXAxis =
      lineSeries.length > 0 ? lineSeries[0].series.map((point: DataPoint) => point.name) : [];
    const lineSeriesOptions: LineSeriesOption[] = lineSeries.map((series: any) => ({
      name: series.name,
      type: 'line',
      smooth: true,
      data: series.series.map((point: DataPoint) => point.value),
    }));

    this.lineOptions = {
      color: this.chartPalette,
      tooltip: { trigger: 'axis' },
      legend: { show: this.showLegend, data: lineSeries.map((series: any) => series.name) },
      grid: { left: 50, right: 20, top: 40, bottom: 50 },
      xAxis: {
        type: 'category',
        data: lineXAxis,
        name: this.xAxisLabel,
        nameLocation: 'middle',
        nameGap: 30,
      },
      yAxis: {
        type: 'value',
        name: this.yAxisLabel,
        nameLocation: 'middle',
        nameGap: 40,
      },
      series: lineSeriesOptions,
    };

    const distribution = this.chartData.scoreDistribution ?? [];
    const barCategories = distribution.map((item: any) => item.name);
    const barValues = distribution.map((item: any) => item.value);

    this.barOptions = {
      color: this.chartPalette,
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 40, bottom: 50 },
      xAxis: {
        type: 'category',
        data: barCategories,
        name: this.distributionXAxisLabel,
        nameLocation: 'middle',
        nameGap: 30,
      },
      yAxis: {
        type: 'value',
        name: this.distributionYAxisLabel,
        nameLocation: 'middle',
        nameGap: 40,
      },
      series: [
        {
          name: 'Distribution',
          type: 'bar',
          data: barValues,
        } as BarSeriesOption,
      ],
    };
  }

  // MOCK DATA HELPER - DELETE WHEN FUNCTIONALITY IS FINALIZED
  // private testWithMockData(mockData: any[]): void {
  //   console.log('Testing with mock data:', mockData.length, 'submissions');

  //   this.rawSubmissions = mockData;

  //   this.chartData = this.vizService.processDataForCharts(mockData);

  //   console.log('Chart data processed:', {
  //     scoreTrends: this.chartData?.scoreTrends.length,
  //     scoreDistribution: this.chartData?.scoreDistribution.length,
  //     moodMeterData: this.chartData?.moodMeterData.length,
  //     statistics: this.chartData?.statistics,
  //   });
  //   console.log(this.chartData?.scoreTrends);
  // }

  // //MOCK DATA HELPER - DELETE WHEN FUNCTIONALITY IS FINALIZED
  // private generateCompleteMockData(): any[] {
  //   const mockData = [];
  //   const today = new Date();
  //   const dates: any[] = [];
  //   for (let i = 14; i >= 0; i--) {
  //     const date = new Date(today);
  //     date.setDate(date.getDate() - i);
  //     dates.push(date.toISOString());
  //   }

  //   // Quiz 1 submissions - 20 students
  //   for (let i = 0; i < 20; i++) {
  //     const baseScore = 70 + Math.random() * 25;
  //     mockData.push({
  //       id: i + 1,
  //       assignmentId: 10,
  //       studentId: 100 + i,
  //       submittedAt: dates[Math.floor(Math.random() * 5)],
  //       score: Math.round(baseScore * 10) / 10,
  //       status: 'GRADED',
  //       answers: [
  //         { questionId: 1, type: 'MULTIPLE_CHOICE', data: { selected: [0] } },
  //       ],
  //     });
  //   }

  //   // Quiz 2 submissions - 18 students
  //   for (let i = 0; i < 18; i++) {
  //     const baseScore = 75 + Math.random() * 20;
  //     mockData.push({
  //       id: i + 21,
  //       assignmentId: 11,
  //       studentId: 100 + i,
  //       submittedAt: dates[5 + Math.floor(Math.random() * 5)],
  //       score: Math.round(baseScore * 10) / 10,
  //       status: 'GRADED',
  //       answers: [
  //         { questionId: 1, type: 'MULTIPLE_CHOICE', data: { selected: [1] } },
  //       ],
  //     });
  //   }

  //   // Quiz 3 submissions - 22 students
  //   for (let i = 0; i < 22; i++) {
  //     const baseScore = 65 + Math.random() * 30;
  //     mockData.push({
  //       id: i + 39,
  //       assignmentId: 12,
  //       studentId: 100 + i,
  //       submittedAt: dates[10 + Math.floor(Math.random() * 5)],
  //       score: Math.round(baseScore * 10) / 10,
  //       status: 'GRADED',
  //       answers: [
  //         { questionId: 1, type: 'MULTIPLE_CHOICE', data: { selected: [2] } },
  //       ],
  //     });
  //   }

  //   // MOOD METER DATA (for heatmap)
  //   const week1MoodData = [
  //     { row: 1, col: 7 }, // Motivated
  //     { row: 1, col: 7 }, // Motivated
  //     { row: 1, col: 7 }, // Motivated
  //     { row: 2, col: 7 }, // Excited
  //     { row: 2, col: 7 }, // Excited
  //     { row: 3, col: 7 }, // Happy
  //     { row: 3, col: 7 }, // Happy
  //     { row: 3, col: 8 }, // Proud

  //     { row: 7, col: 7 }, // Restful
  //     { row: 7, col: 7 }, // Restful
  //     { row: 8, col: 7 }, // Peaceful
  //     { row: 8, col: 7 }, // Peaceful
  //     { row: 6, col: 7 }, // Satisfied
  //     { row: 6, col: 6 }, // Secure

  //     { row: 3, col: 2 }, // Worried
  //     { row: 4, col: 3 }, // Uneasy
  //     { row: 2, col: 3 }, // Nervous

  //     { row: 7, col: 4 }, // Tired
  //     { row: 6, col: 4 }, // Bored
  //     { row: 6, col: 3 }, // Sad
  //   ];

  //   week1MoodData.forEach((mood, index) => {
  //     mockData.push({
  //       id: 100 + index,
  //       assignmentId: 1,
  //       studentId: 100 + index,
  //       submittedAt: dates[Math.floor(Math.random() * 3)],
  //       score: null,
  //       status: 'SUBMITTED',
  //       answers: [{ questionId: 1, type: 'MOOD_METER', data: mood }],
  //     });
  //   });

  //   const week2MoodData = [
  //     { row: 0, col: 2 }, // Stressed
  //     { row: 0, col: 2 }, // Stressed
  //     { row: 0, col: 2 }, // Stressed
  //     { row: 0, col: 2 }, // Stressed
  //     { row: 2, col: 3 }, // Nervous
  //     { row: 2, col: 3 }, // Nervous
  //     { row: 2, col: 3 }, // Nervous
  //     { row: 3, col: 2 }, // Worried
  //     { row: 3, col: 2 }, // Worried
  //     { row: 3, col: 2 }, // Worried
  //     { row: 1, col: 2 }, // Frustrated
  //     { row: 4, col: 3 }, // Uneasy

  //     { row: 2, col: 7 }, // Excited
  //     { row: 3, col: 6 }, // Focused
  //     { row: 3, col: 6 }, // Focused
  //     { row: 1, col: 7 }, // Motivated
  //     { row: 3, col: 7 }, // Happy

  //     { row: 7, col: 4 }, // Tired
  //     { row: 7, col: 4 }, // Tired
  //     { row: 8, col: 3 }, // Exhausted
  //     { row: 8, col: 3 }, // Exhausted
  //     { row: 8, col: 4 }, // Fatigued
  //     { row: 6, col: 3 }, // Sad

  //     { row: 7, col: 7 }, // Restful
  //     { row: 8, col: 7 }, // Peaceful
  //   ];

  //   week2MoodData.forEach((mood, index) => {
  //     mockData.push({
  //       id: 150 + index,
  //       assignmentId: 1,
  //       studentId: 100 + (index % 25),
  //       submittedAt: dates[7 + Math.floor(Math.random() * 4)],
  //       score: null,
  //       status: 'SUBMITTED',
  //       answers: [{ questionId: 1, type: 'MOOD_METER', data: mood }],
  //     });
  //   });

  //   return mockData;
  // }

  // MOCK DATA HELPER - DELETE WHEN FUNCTIONALITY IS FINALIZED
  // THIS IS THE FUNCTION INTENDED TO SIMULATE LARGE SUBMISSION HISTORY
  // private generateCompleteMockData(): any[] {
  //   const mockData = [];
  //   const startDate = new Date('2025-01-01');
  //   let submissionId = 1;
  //   const assignmentIdStart = 10;

  //   for (let week = 0; week < 36; week++) {
  //     const assignmentId = assignmentIdStart + week;

  //     const weekStartDate = new Date(startDate);
  //     weekStartDate.setDate(startDate.getDate() + week * 7);

  //     for (let student = 0; student < 30; student++) {
  //       const submissionDate = new Date(weekStartDate);
  //       submissionDate.setDate(
  //         weekStartDate.getDate() + Math.floor(Math.random() * 7)
  //       );
  //       submissionDate.setHours(Math.floor(Math.random() * 24));
  //       submissionDate.setMinutes(Math.floor(Math.random() * 60));
  //       const score = Math.round(Math.random() * 100 * 10) / 10;

  //       mockData.push({
  //         id: submissionId++,
  //         assignmentId: assignmentId,
  //         studentId: 100 + student,
  //         submittedAt: submissionDate.toISOString(),
  //         score: score,
  //         status: 'GRADED',
  //         answers: [
  //           {
  //             questionId: 1,
  //             type: 'MULTIPLE_CHOICE',
  //             data: { selected: [Math.floor(Math.random() * 4)] },
  //           },
  //         ],
  //       });
  //     }
  //   }

  //   return mockData;
  // }
}
