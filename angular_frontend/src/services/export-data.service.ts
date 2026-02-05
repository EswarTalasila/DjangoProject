import { Injectable } from '@angular/core';
import {
  ProcessedChartData,
  VisualizationSubmission,
} from './visualization.service';
import jsPDF from 'jspdf';
import { svg2pdf } from 'svg2pdf.js';
import { DialogService } from './dialog.service';

@Injectable({
  providedIn: 'root',
})
export class ExportService {

  constructor(private dialogService: DialogService) {}

  exportToCSV(
    submissions: VisualizationSubmission[],
    chartData: ProcessedChartData,
    filters: any,
  ): void {
    const csvRows: string[] = [];

    csvRows.push('Visualization Export');
    csvRows.push(`Export Date: ${new Date().toLocaleString()}`);
    csvRows.push('');
    csvRows.push('Applied Filters:');
    csvRows.push(`Course ID: ${filters.courseId || 'All'}`);
    csvRows.push(`Student ID: ${filters.studentId || 'All'}`);
    csvRows.push(`Category: ${filters.category || 'All'}`);
    csvRows.push(`Assessment ID: ${filters.assessmentId || 'All'}`);
    csvRows.push(`Teacher ID: ${filters.teacherId || 'All'}`);
    csvRows.push(`Mood Meter: ${filters.isMoodMeter ? 'Yes' : 'No'}`);
    csvRows.push('');
    csvRows.push('Statistics:');
    csvRows.push(`Mean Score: ${chartData.statistics.mean}`);
    csvRows.push(`Median Score: ${chartData.statistics.median}`);
    csvRows.push(`Standard Deviation: ${chartData.statistics.stdDev}`);
    csvRows.push(`Total Submissions: ${chartData.statistics.count}`);
    csvRows.push('');

    csvRows.push('Submission Details:');
    const headers = [
      'ID',
      'Assignment ID',
      'Student ID',
      'Submitted At',
      'Score',
      'Status',
      'Course Name',
      'Assessment Title',
    ];
    csvRows.push(headers.join(','));

    submissions.forEach((sub) => {
      const row = [
        sub.id,
        sub.assignmentId,
        sub.studentId || '',
        sub.submittedAt,
        sub.score !== null && sub.score !== undefined ? sub.score : '',
        sub.status,
        sub.courseName || '',
        sub.assessmentTitle || '',
      ];
      csvRows.push(row.map((field) => `"${field}"`).join(','));
    });

    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    const timestamp = this.getFormattedTimestamp();
    link.setAttribute('href', url);
    link.setAttribute('download', `visualization_export_${timestamp}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async exportToPDF(
    chartData: ProcessedChartData,
    filters: any,
  ): Promise<void> {
    try {
      await this.delay(1500);

      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const margin = 15;
      const contentWidth = pdfWidth - 2 * margin;

      pdf.setFontSize(20);
      pdf.text('Visualization Report', pdfWidth / 2, 20, { align: 'center' });

      pdf.setFontSize(10);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, pdfWidth / 2, 28, {
        align: 'center',
      });

      let yPos = 40;

      pdf.setFontSize(14);
      pdf.text('Applied Filters', margin, yPos);
      yPos += 8;

      pdf.setFontSize(10);
      const filterText = [
        `Course: ${filters.courseId || 'All'}`,
        `Student: ${filters.studentId || 'All'}`,
        `Category: ${filters.category || 'All'}`,
        `Assessment: ${filters.assessmentId || 'All'}`,
      ];

      filterText.forEach((text) => {
        pdf.text(text, margin + 5, yPos);
        yPos += 6;
      });

      yPos += 5;

      pdf.setFontSize(14);
      pdf.text('Statistics', margin, yPos);
      yPos += 8;

      pdf.setFontSize(10);
      const statsText = [
        `Mean Score: ${chartData.statistics.mean}`,
        `Median Score: ${chartData.statistics.median}`,
        `Standard Deviation: ${chartData.statistics.stdDev}`,
        `Total Submissions: ${chartData.statistics.count}`,
      ];

      statsText.forEach((text) => {
        pdf.text(text, margin + 5, yPos);
        yPos += 6;
      });

      const chartContainers = document.querySelectorAll('.chart-container');

      for (let i = 0; i < chartContainers.length; i++) {
        const container = chartContainers[i] as HTMLElement;
        const svg = container.querySelector('svg');
        if (!svg) continue;
        pdf.addPage();
        yPos = 20;

        const titleElement = container.querySelector('.chart-header h3');
        const title = titleElement?.textContent || `Chart ${i + 1}`;

        pdf.setFontSize(14);
        pdf.text(title, margin, yPos);
        yPos += 10;

        const svgRect = svg.getBoundingClientRect();
        const svgWidth = svgRect.width;
        const svgHeight = svgRect.height;

        const maxChartHeight = pdfHeight - yPos - margin;
        let scale = 1;

        if (svgWidth > contentWidth) {
          scale = contentWidth / svgWidth;
        }

        const scaledHeight = svgHeight * scale;
        if (scaledHeight > maxChartHeight) {
          scale = maxChartHeight / svgHeight;
        }

        const finalWidth = svgWidth * scale;
        const finalHeight = svgHeight * scale;

        const xPos = margin + (contentWidth - finalWidth) / 2;

        try {
          const clonedSVG = svg.cloneNode(true) as SVGElement;

          if (!clonedSVG.getAttribute('viewBox')) {
            clonedSVG.setAttribute('viewBox', `0 0 ${svgWidth} ${svgHeight}`);
          }

          await svg2pdf(clonedSVG, pdf, {
            x: xPos,
            y: yPos,
            width: finalWidth,
            height: finalHeight,
          });
        } catch (err) {
          console.error(`Error exporting chart ${i}:`, err);
          pdf.setFontSize(10);
          pdf.text('Error: Chart could not be exported', margin, yPos + 20);
        }
      }

      const timestamp = this.getFormattedTimestamp();
      pdf.save(`visualization_report_${timestamp}.pdf`);
    } catch (error) {
      console.error('Error generating PDF:', error);
      this.dialogService.showRobustDialog('Failed to generate', 'Failed to generate PDF. Please try again.', 'error');
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private getFormattedTimestamp(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    return `${year}${month}${day}_${hours}${minutes}${seconds}`;
  }
}
