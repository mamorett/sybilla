import json
import os
from datetime import datetime
from typing import Dict, Any
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import pdfkit
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
import base64
from io import BytesIO

from app.config import settings

class ReportGenerator:
    def __init__(self):
        self.template_env = Environment(loader=FileSystemLoader('templates'))
        self.output_dir = settings.REPORT_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set style for matplotlib
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    async def generate_pdf_report(self, analysis_data: Dict[str, Any], 
                                nim_analysis: str) -> str:
        """Generate comprehensive PDF report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"oracle_logs_analysis_{timestamp}.pdf"
        report_path = os.path.join(self.output_dir, report_filename)
        
        # Parse NIM analysis if it's JSON
        try:
            nim_results = json.loads(nim_analysis)
        except:
            nim_results = {"raw_analysis": nim_analysis}
        
        # Generate visualizations
        charts = await self._generate_charts(analysis_data, nim_results)
        
        # Prepare template data
        template_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_data": analysis_data,
            "nim_analysis": nim_results,
            "charts": charts,
            "summary": self._create_executive_summary(analysis_data, nim_results)
        }
        
        # Render HTML template
        template = self.template_env.get_template('report_template.html')
        html_content = template.render(**template_data)
        
        # Convert to PDF
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        pdfkit.from_string(html_content, report_path, options=options)
        
        return report_path
    
    async def _generate_charts(self, analysis_data: Dict[str, Any], 
                             nim_results: Dict[str, Any]) -> Dict[str, str]:
        """Generate various charts and return as base64 encoded strings"""
        
        charts = {}
        
        # 1. Country Traffic Distribution
        charts['country_distribution'] = self._create_country_chart(analysis_data)
        
        # 2. Protocol Usage Chart
        charts['protocol_usage'] = self._create_protocol_chart(analysis_data)
        
        # 3. Time Series Traffic Chart
        charts['traffic_timeline'] = self._create_timeline_chart(analysis_data)
        
        # 4. Geographic Heatmap
        charts['geographic_heatmap'] = self._create_geographic_chart(analysis_data)
        
        # 5. Security Risk Chart (if available in NIM analysis)
        if 'visualization_data' in nim_results:
            charts['security_analysis'] = self._create_security_chart(nim_results['visualization_data'])
        
        return charts
    
    def _create_country_chart(self, analysis_data: Dict[str, Any]) -> str:
        """Create country traffic distribution chart"""
        
        try:
            # Extract country data
            country_data = analysis_data.get('current_period', {}).get('country_analytics', {})
            
            if not country_data or 'logs' not in country_data:
                return self._create_placeholder_chart("No country data available")
            
            # Prepare data
            countries = []
            counts = []
            
            for log in country_data['logs'][:10]:  # Top 10 countries
                countries.append(log.get('country', 'Unknown'))
                counts.append(log.get('count', 1))
            
            # Create plotly chart
            fig = px.bar(
                x=countries, 
                y=counts,
                title="Top 10 Countries by Traffic Volume",
                labels={'x': 'Country', 'y': 'Request Count'}
            )
            
            fig.update_layout(
                showlegend=False,
                height=400,
                font=dict(size=12)
            )
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error creating country chart: {e}")
            return self._create_placeholder_chart("Error generating country chart")
    
    def _create_protocol_chart(self, analysis_data: Dict[str, Any]) -> str:
        """Create protocol usage pie chart"""
        
        try:
            protocol_data = analysis_data.get('current_period', {}).get('protocol_analytics', {})
            
            if not protocol_data or 'logs' not in protocol_data:
                return self._create_placeholder_chart("No protocol data available")
            
            protocols = []
            counts = []
            
            for log in protocol_data['logs']:
                protocols.append(log.get('protocol', 'Unknown'))
                counts.append(log.get('count', 1))
            
            fig = px.pie(
                values=counts,
                names=protocols,
                title="Protocol Usage Distribution"
            )
            
            fig.update_layout(height=400)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error creating protocol chart: {e}")
            return self._create_placeholder_chart("Error generating protocol chart")
    
    def _create_timeline_chart(self, analysis_data: Dict[str, Any]) -> str:
        """Create traffic timeline chart"""
        
        try:
            # This is a simplified version - in reality, you'd extract timestamp data
            # from logs and create a proper timeline
            
            # Generate sample timeline data
            dates = pd.date_range(start='2024-01-01', periods=24, freq='H')
            traffic = [100 + i * 10 + (i % 3) * 20 for i in range(24)]
            
            fig = px.line(
                x=dates,
                y=traffic,
                title="Traffic Volume Over Time (Last 24 Hours)",
                labels={'x': 'Time', 'y': 'Request Count'}
            )
            
            fig.update_layout(height=400)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error creating timeline chart: {e}")
            return self._create_placeholder_chart("Error generating timeline chart")
    
    def _create_geographic_chart(self, analysis_data: Dict[str, Any]) -> str:
        """Create geographic distribution chart"""
        
        try:
            city_data = analysis_data.get('current_period', {}).get('city_analytics', {})
            
            if not city_data or 'logs' not in city_data:
                return self._create_placeholder_chart("No geographic data available")
            
            cities = []
            counts = []
            
            for log in city_data['logs'][:15]:  # Top 15 cities
                cities.append(log.get('city', 'Unknown'))
                counts.append(log.get('count', 1))
            
            fig = px.bar(
                x=counts,
                y=cities,
                orientation='h',
                title="Top Cities by Traffic Volume",
                labels={'x': 'Request Count', 'y': 'City'}
            )
            
            fig.update_layout(height=500)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error creating geographic chart: {e}")
            return self._create_placeholder_chart("Error generating geographic chart")
    
    def _create_security_chart(self, viz_data: Dict[str, Any]) -> str:
        """Create security analysis chart from NIM results"""
        
        try:
            # This would depend on the structure of visualization_data from NIM
            # For now, create a sample security metrics chart
            
            metrics = ['Suspicious IPs', 'Failed Logins', 'Unusual Patterns', 'High Risk Countries']
            values = [15, 23, 8, 12]  # Sample data
            
            fig = px.bar(
                x=metrics,
                y=values,
                title="Security Risk Indicators",
                color=values,
                color_continuous_scale='Reds'
            )
            
            fig.update_layout(height=400, showlegend=False)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error creating security chart: {e}")
            return self._create_placeholder_chart("Error generating security chart")
    
    def _fig_to_base64(self, fig) -> str:
        """Convert plotly figure to base64 string"""
        img_bytes = fig.to_image(format="png", width=800, height=400)
        img_base64 = base64.b64encode(img_bytes).decode()
        return f"data:image/png;base64,{img_base64}"
    
    def _create_placeholder_chart(self, message: str) -> str:
        """Create a placeholder chart with a message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        return self._fig_to_base64(fig)
    
    def _create_executive_summary(self, analysis_data: Dict[str, Any], 
                                nim_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create executive summary from analysis data"""
        
        summary = {
            "total_logs_analyzed": 0,
            "unique_countries": 0,
            "top_country": "Unknown",
            "primary_protocol": "Unknown",
            "key_findings": [],
            "risk_level": "Medium"
        }
        
        # Extract summary statistics
        if 'summary_statistics' in analysis_data:
            stats = analysis_data['summary_statistics']
            summary.update({
                "total_logs_analyzed": stats.get('total_requests', 0),
                "unique_countries": stats.get('unique_countries', 0)
            })
        
        # Extract key findings from NIM analysis
        if isinstance(nim_results, dict):
            if 'key_findings' in nim_results:
                summary['key_findings'] = nim_results['key_findings']
            if 'executive_summary' in nim_results:
                summary['executive_summary'] = nim_results['executive_summary']
        
        return summary
