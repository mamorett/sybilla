# app/services/report_generator.py
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import io
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
        # Set matplotlib to use non-interactive backend
        plt.switch_backend('Agg')
        plt.style.use('default')  # Use default style to avoid seaborn issues
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        ))
    
    async def generate_pdf_report(self, analysis_data: Dict[str, Any], nim_analysis: Dict[str, Any]) -> str:
        """Generate PDF report - simplified version"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = f"/tmp/oracle_analysis_report_{timestamp}.pdf"
            
            logger.info("📊 Generating PDF report...")
            
            # Create the PDF document
            doc = SimpleDocTemplate(report_path, pagesize=A4)
            story = []
            
            # Title
            story.append(Paragraph("Oracle Cloud Infrastructure Analysis Report", self.styles['CustomTitle']))
            story.append(Spacer(1, 30))
            
            # Report info
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['Normal']))
            story.append(Paragraph(f"Analysis Period: {analysis_data.get('time_range', '24 hours')}", self.styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Summary statistics
            story.append(Paragraph("Summary Statistics", self.styles['CustomHeading']))
            stats = analysis_data.get("summary_statistics", {})
            
            summary_text = f"""
            Total Log Entries: {stats.get('total_logs', 0):,}<br/>
            Total Data Volume: {stats.get('total_bytes', 0) / (1024*1024):.1f} MB<br/>
            Average Entry Size: {stats.get('avg_bytes_per_log', 0):.0f} bytes<br/>
            Countries Analyzed: {len(analysis_data.get('country_analytics', {}).get('analytics', []))}<br/>
            """
            
            story.append(Paragraph(summary_text, self.styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Country analytics
            country_data = analysis_data.get('country_analytics', {}).get('analytics', [])
            if country_data:
                story.append(Paragraph("Top Countries by Traffic", self.styles['CustomHeading']))
                
                # Create table
                table_data = [["Country", "Requests", "Bytes"]]
                for item in country_data[:10]:  # Top 10
                    table_data.append([
                        item.get('country', 'Unknown'),
                        f"{item.get('request_count', 0):,}",
                        f"{item.get('total_bytes', 0):,}"
                    ])
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 20))
            
            # AI Analysis
            story.append(PageBreak())
            story.append(Paragraph("AI Analysis Results", self.styles['CustomHeading']))
            
            if isinstance(nim_analysis, dict):
                for key, value in nim_analysis.items():
                    if key not in ['raw_response']:  # Skip raw data
                        story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b>", self.styles['Normal']))
                        story.append(Paragraph(str(value), self.styles['Normal']))
                        story.append(Spacer(1, 10))
            else:
                story.append(Paragraph(str(nim_analysis), self.styles['Normal']))
            
            # Generate simple chart
            chart_path = self._create_simple_chart(country_data)
            if chart_path and os.path.exists(chart_path):
                story.append(PageBreak())
                story.append(Paragraph("Traffic Distribution Chart", self.styles['CustomHeading']))
                try:
                    img = Image(chart_path, width=6*inch, height=4*inch)
                    story.append(img)
                except Exception as e:
                    logger.warning(f"Could not add chart to PDF: {e}")
                    story.append(Paragraph("Chart generation failed", self.styles['Normal']))
                
                # Cleanup chart file
                try:
                    os.remove(chart_path)
                except:
                    pass
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"✅ PDF report generated: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"❌ PDF generation failed: {e}")
            raise
    
    def _create_simple_chart(self, country_data: List[Dict]) -> str:
        """Create a simple chart"""
        try:
            if not country_data:
                return None
            
            chart_path = f"/tmp/chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Prepare data
            countries = [item.get('country', 'Unknown')[:10] for item in country_data[:8]]  # Top 8, short names
            requests = [item.get('request_count', 0) for item in country_data[:8]]
            
            # Create chart
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(countries, requests, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'])
            
            ax.set_title('Top Countries by Request Count', fontsize=14, fontweight='bold')
            ax.set_xlabel('Country')
            ax.set_ylabel('Request Count')
            ax.tick_params(axis='x', rotation=45)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height):,}', ha='center', va='bottom', fontsize=8)
            
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logger.warning(f"Chart creation failed: {e}")
            return None
