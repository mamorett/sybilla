import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import schedule
import time
from threading import Thread
import os
import json
from app.services.mcp_client import MCPClient
from app.services.nvidia_nim_client import NVIDIANIMClient
from app.services.oci_storage_client import OCIStorageClient
from app.services.analytics_services import AnalyticsService
from app.services.markdown_generator import MarkdownGenerator  # Changed from ReportGenerator
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalysisScheduler:
    def __init__(self):
        """Initialize the analysis scheduler"""
        self.mcp_client = MCPClient()  # Connects to your existing MCP server
        self.nim_client = NVIDIANIMClient()
        self.oci_client = OCIStorageClient()
        self.analytics_service = AnalyticsService()
        self.markdown_generator = MarkdownGenerator()  # Changed from report_generator
        self.is_running = False
        self.scheduler_thread: Optional[Thread] = None
        self.last_analysis_result: Optional[Dict[str, Any]] = None
        
        logger.info("📅 Analysis Scheduler initialized")
        logger.info(f"🔧 MCP Server Script: {settings.MCP_SERVER_SCRIPT_PATH}")
        logger.info(f"⏰ Analysis Interval: {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")
    


    def _create_analysis_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Create a comprehensive analysis prompt for NIM - REENGINEERED FOR COMMAND GENERATION"""
        
        # Extract key statistics
        stats = analysis_data.get("summary_statistics", {})
        total_logs = stats.get("total_requests", 0)
        
        # Get the actual data from current_period
        current_period = analysis_data.get("current_period", {})
        country_analytics = current_period.get("country_analytics", {})
        
        # Extract top countries from the correct structure
        country_distribution = country_analytics.get("country_distribution", {})
        top_countries = list(country_distribution.keys())[:5] if country_distribution else []
        
        # Extract sensors from sensor analytics
        sensor_analytics = current_period.get("sensor_analytics", {})
        sensor_distribution = sensor_analytics.get("sensor_distribution", {})
        sensors = list(sensor_distribution.keys()) if sensor_distribution else []

        # Extract ISP data
        isp_analytics = current_period.get("isp_analytics", {})
        isp_distribution = isp_analytics.get("isp_distribution", {})

        # Extract threat indicators from IP analytics
        ip_analytics = current_period.get("ip_analytics", {})
        threat_indicators = ip_analytics.get("threat_indicators", {})
        ssh_violators = threat_indicators.get("ssh_outside_budapest", [])
        multi_sensor_violators = threat_indicators.get("multiple_sensors", {})

        # Collect ALL suspicious IPs for command generation
        all_suspicious_ips = set()
        
        # Add SSH violators
        if ssh_violators:
            all_suspicious_ips.update(ssh_violators)
        
        # Add multi-sensor violators
        if multi_sensor_violators:
            all_suspicious_ips.update(multi_sensor_violators.keys())
        
        # Convert to sorted list for consistent output
        suspicious_ip_list = sorted(list(all_suspicious_ips))

        # Format distributions for readable prompt
        country_list = "\n".join([f"  {country}: {count:,}" for country, count in list(country_distribution.items())[:10]])
        sensor_list = "\n".join([f"  {sensor}: {count:,}" for sensor, count in sensor_distribution.items()])
        isp_list = "\n".join([f"  {isp}: {count:,}" for isp, count in list(isp_distribution.items())[:10]])
        ssh_violators_list = "\n".join([f"  - {ip}" for ip in ssh_violators]) if ssh_violators else "  - None detected."
        multi_sensor_list = "\n".join([f"  - {ip}: {', '.join(sensors)}" for ip, sensors in list(multi_sensor_violators.items())[:10]]) if multi_sensor_violators else "  - None detected."
        
        # Create explicit IP list for commands
        suspicious_ips_formatted = "\n".join([f"  - {ip}" for ip in suspicious_ip_list]) if suspicious_ip_list else "  - None detected."
        
        # PRE-GENERATE the exact commands we want
        if suspicious_ip_list:
            expected_commands = [f"iptables -A INPUT -s {ip} -j DROP" for ip in suspicious_ip_list]
            expected_commands.extend([
                "iptables -L INPUT -n | grep DROP",
                "iptables-save > /etc/iptables/rules.v4",
                "systemctl restart iptables"
            ])
            commands_example = '",\n        "'.join(expected_commands)
        else:
            expected_commands = [
                "iptables -L INPUT -n"
            ]
            commands_example = '",\n        "'.join(expected_commands) 
        
        prompt = f"""You are a cybersecurity analyst. Analyze this log data and provide actionable security recommendations with specific commands.

    ## CRITICAL: You MUST provide a JSON response with the exact structure shown below.

    ## Data Summary:
    - Total log entries: {total_logs:,}
    - Unique IPs: {stats.get('unique_ips', 0)}
    - Unique countries: {stats.get('unique_countries', 0)}
    - Time range: {current_period.get('time_range', '24h')}

    ## Traffic Distribution:
    ### Top Countries:
    {country_list}

    ### Sensors/Services:
    {sensor_list}

    ### Top ISPs:
    {isp_list}

    ## SECURITY THREATS DETECTED:

    ### Suspicious IPs connecting to SSH from outside Budapest:
    {ssh_violators_list}

    ### IPs scanning multiple sensors (potential reconnaissance):
    {multi_sensor_list}

    ### ALL SUSPICIOUS IPs REQUIRING IMMEDIATE BLOCKING:
    {suspicious_ips_formatted}

    ## REQUIRED JSON RESPONSE FORMAT:

    You MUST respond with a JSON object containing these exact fields:

    ```json
    {{
        "executive_summary": "Brief 2-3 sentence summary of findings and risk level",
        "risk_level": "Low|Medium|High|Critical",
        "security_analysis": "Detailed analysis of threats and security concerns",
        "key_findings": [
            "List of 3-5 most important observations",
            "Include specific IP addresses and threat types",
            "Mention geographic anomalies"
        ],
        "recommendations": [
            "List of 3-5 specific actionable recommendations",
            "Include immediate and long-term actions",
            "Reference the suspicious IPs found"
        ],
        "suggested_commands": [
            "{commands_example}"
        ],        
        "immediate_actions": [
            "List urgent actions to take within 24 hours",
            "Include investigation steps for specific IPs"
        ],
        "confidence": "High|Medium|Low",
        "analysis_method": "NVIDIA NIM Analysis of Oracle Cloud logs"
    }}

    ```

    **In the supplementary text outside the JSON block, you can provide:**
    -   Further explanations of your findings.
    -   Deeper insights into the traffic patterns.
    -   Context for your recommendations.

    COMMAND GENERATION RULES:
    - MANDATORY: Generate iptables -A INPUT -s <IP> -j DROP for EVERY IP in the suspicious list above
    - If no suspicious IPs: Provide monitoring commands instead
    - Always include: At least 3-5 actionable commands
    - Format: Each command must be a complete, executable bash command string
    SPECIFIC REQUIREMENTS:
    - Risk Assessment: Evaluate based on SSH access from unexpected locations and multi-sensor scanning
    - Geographic Analysis: Flag connections from outside expected regions (Budapest area expected for SSH)
    - Command Priority: Block suspicious IPs first, then add monitoring commands
    - Actionable Focus: Every recommendation must have a corresponding command or investigation step
    EXAMPLE COMMANDS TO INCLUDE:
    - iptables -A INPUT -s 198.55.98.176 -j DROP (for each suspicious IP)
    - iptables -L INPUT -n | grep DROP (to verify blocks)
    - tail -f /var/log/auth.log | grep "Failed password" (for SSH monitoring)
    - netstat -an | grep :22 | grep ESTABLISHED (check active SSH connections)
    Generate your analysis focusing on the {len(suspicious_ip_list)} suspicious IPs detected and provide immediate blocking commands for each one."""  
        
        return prompt.strip()


    def _generate_security_commands(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate security commands and analysis - returns data for the REPORT"""
        
        # Extract suspicious IPs
        current_period = analysis_data.get("current_period", {})
        ip_analytics = current_period.get("ip_analytics", {})
        threat_indicators = ip_analytics.get("threat_indicators", {})
        
        ssh_violators = threat_indicators.get("ssh_outside_budapest", [])
        multi_sensor_violators = threat_indicators.get("multiple_sensors", {})
        
        # Collect suspicious IPs
        suspicious_ips = set(ssh_violators)
        suspicious_ips.update(multi_sensor_violators.keys())
        suspicious_ips = sorted(list(suspicious_ips))
        
        commands = []
        
        if suspicious_ips:
            # Block each suspicious IP
            for ip in suspicious_ips:
                commands.append(f"iptables -A INPUT -s {ip} -j DROP")
            
            # Add verification
            commands.append("iptables -L INPUT -n | grep DROP")
            commands.append("iptables-save > /etc/iptables/rules.v4")
            
            executive_summary = f"SECURITY ALERT: {len(suspicious_ips)} malicious IPs detected: {', '.join(suspicious_ips)}. Immediate blocking required."
            risk_level = "High"
            key_findings = [
                f"SSH attacks from outside Budapest: {', '.join(ssh_violators)}" if ssh_violators else "No SSH attacks detected",
                f"Port scanning from: {', '.join(multi_sensor_violators.keys())}" if multi_sensor_violators else "No port scanning detected",
                f"Total malicious IPs to block: {len(suspicious_ips)}"
            ]
            recommendations = [
                f"Execute the {len(commands)} iptables commands below immediately",
                "Monitor /var/log/auth.log for continued attacks",
                "Consider implementing fail2ban for automated blocking"
            ]
        else:
            # No threats - monitoring commands
            commands = [
                "iptables -L INPUT -n"
            ]
            
            executive_summary = "No immediate security threats detected. System appears secure."
            risk_level = "Low"
            key_findings = [
                "No suspicious SSH attempts from outside Budapest",
                "No port scanning activity detected",
                "All traffic appears legitimate"
            ]
            recommendations = [
                "Continue monitoring with the commands provided below",
                "Review logs periodically for new threats",
                "Maintain current security posture"
            ]
        
        return {
            "executive_summary": executive_summary,
            "risk_level": risk_level,
            "security_analysis": f"Automated analysis of Oracle Cloud logs identified {len(suspicious_ips)} suspicious IP addresses requiring immediate action.",
            "key_findings": key_findings,
            "recommendations": recommendations,
            "suggested_commands": commands,
            "confidence": "High",
            "analysis_method": "Automated Threat Detection"
        }


    def _create_report_directory(self) -> str:
        """Create timestamped report directory"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_dir = f"reports/sybylla-{timestamp}"
        os.makedirs(report_dir, exist_ok=True)
        logger.info(f"📁 Created report directory: {report_dir}")
        return report_dir
    
    async def test_connections(self) -> Dict[str, Any]:
        """Test connections to all external services"""
        logger.info("🔍 Testing connections to external services...")
        
        results = {
            "mcp_connected": False,
            "mcp_tools": [],
            "nim_available": False,
            "oci_available": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Test MCP connection
        try:
            mcp_ok = await self.mcp_client.test_connection()
            results["mcp_connected"] = mcp_ok
            
            if mcp_ok:
                logger.info("✅ MCP Server: Connected to Oracle Logs MCP")
                
                # List available tools
                tools = await self.mcp_client.list_tools()
                if tools:
                    tool_names = [tool.get("name", "unknown") for tool in tools]
                    results["mcp_tools"] = tool_names
                    logger.info(f"🔧 Available MCP tools: {', '.join(tool_names)}")
                else:
                    logger.warning("⚠️ No tools found in MCP server response")
            else:
                logger.error("❌ MCP Server: Connection failed")
                
        except Exception as e:
            logger.error(f"❌ MCP Server connection error: {e}")
            results["mcp_error"] = str(e)
        
        # Test NVIDIA NIM (optional)
        try:
            if settings.NVIDIA_NIM_API_KEY:
                # Simple test - this would need to be implemented in NIM client
                results["nim_available"] = True
                logger.info("✅ NVIDIA NIM: API key configured")
            else:
                logger.info("ℹ️ NVIDIA NIM: No API key configured (optional)")
        except Exception as e:
            logger.warning(f"⚠️ NVIDIA NIM test failed: {e}")
        
        # Test OCI (optional)
        try:
            if settings.OCI_NAMESPACE:
                results["oci_available"] = True
                logger.info("✅ OCI Object Storage: Configuration found")
            else:
                logger.info("ℹ️ OCI Object Storage: Not configured (optional)")
        except Exception as e:
            logger.warning(f"⚠️ OCI test failed: {e}")
        
        return results
    
    async def run_analysis(self) -> Dict[str, Any]:
        """Run a complete analysis cycle"""
        analysis_start_time = datetime.now()
        logger.info("🚀 Starting automated Oracle Logs analysis...")
        
        # Create timestamped report directory
        report_dir = self._create_report_directory()
        
        try:
            # Step 1: Test connections
            logger.info("🔍 Step 1: Testing service connections...")
            connections = await self.test_connections()
            
            if not connections["mcp_connected"]:
                error_msg = "Cannot proceed without MCP server connection"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "timestamp": analysis_start_time.isoformat(),
                    "connections": connections,
                    "report_dir": report_dir
                }
            
            # Step 2: Get analysis prompt
            logger.info("📝 Step 2: Loading analysis prompt...")
            try:
                analysis_prompt = await self.oci_client.get_analysis_prompt()
                logger.info("✅ Analysis prompt loaded from OCI Object Storage")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch prompt from OCI, using default: {e}")
                analysis_prompt = self._get_default_analysis_prompt()
            
            # Step 3: Gather comprehensive log data from your MCP server
            logger.info("📊 Step 3: Gathering log data from Oracle Logs MCP Server...")
            analysis_data = await self.analytics_service.prepare_comprehensive_analysis(
                self.mcp_client
            )
            
            # Log data summary
            stats = analysis_data.get("summary_statistics", {})
            
            logger.info(f"📈 Data gathered: {analysis_data.get('total_requests', 0)} logs, "
                    f"{analysis_data.get('unique_countries', 0)} countries, "
                    f"{analysis_data.get('unique_sensors', 0)} sensors")          
            
            # Step 4: Send data to NVIDIA NIM for AI analysis
            logger.info("🤖 Step 4: Sending data to NVIDIA NIM for analysis...")
            try:
                # Validate analysis_data
                if not isinstance(analysis_data, dict):
                    logger.error(f"❌ Invalid analysis_data type: {type(analysis_data)}")
                    raise ValueError(f"analysis_data must be a dictionary, got {type(analysis_data)}")
                
                logger.info(f"📊 Analysis data keys: {list(analysis_data.keys())}")
                
                # Create THE ONLY analysis prompt (from scheduler)
                analysis_prompt = self._create_analysis_prompt(analysis_data)
                logger.info(f"📝 Generated analysis prompt ({len(analysis_prompt)} characters)")
                
                # Call NIM with the complete prompt
                nim_analysis = await self.nim_client.analyze_logs(analysis_data, analysis_prompt)

                # Log the response structure
                logger.info(f"🤖 NIM analysis type: {type(nim_analysis)}")
                logger.info(f"🤖 NIM analysis keys: {list(nim_analysis.keys())}")
                logger.info(f"🤖 Response type: {nim_analysis.get('response_type', 'unknown')}")
                logger.info(f"🤖 Has JSON: {nim_analysis.get('has_json', False)}")
                logger.info(f"🤖 Has additional content: {nim_analysis.get('has_additional_content', False)}")
                
                # Validate we have the required fields
                required_fields = ['executive_summary', 'risk_level', 'recommendations']
                missing_fields = [field for field in required_fields if not nim_analysis.get(field)]
                
                if missing_fields:
                    logger.warning(f"⚠️ Missing required fields: {missing_fields}")
                else:
                    logger.info("✅ All required fields present in response")
                
                logger.info("✅ AI analysis completed successfully")

                # Always generate our own analysis with commands
                automated_analysis = self._generate_security_commands(analysis_data)

                # Use AI analysis if available, otherwise use automated
                if nim_analysis and isinstance(nim_analysis, dict):
                    logger.info("✅ Security analysis ready for report generation")                
                    # Merge AI analysis with our guaranteed commands
                    nim_analysis["suggested_commands"] = automated_analysis["suggested_commands"]
                    # Ensure we have all required fields
                    for key in ["executive_summary", "risk_level", "key_findings", "recommendations"]:
                        if key not in nim_analysis:
                            nim_analysis[key] = automated_analysis[key]
                else:
                    # Use our automated analysis
                    nim_analysis = automated_analysis
                
            except Exception as e:
                logger.error(f"❌ NIM analysis failed: {e}")
                logger.error(f"❌ Exception type: {type(e).__name__}")
                
                # Create comprehensive fallback analysis
                nim_analysis = {
                    "executive_summary": f"AI analysis encountered an error: {str(e)}. Manual review of log data is recommended.",
                    "risk_level": "Unknown",
                    "security_analysis": "Automated security analysis was not completed due to service issues.",
                    "key_findings": [
                        "AI analysis service unavailable",
                        "Manual review required",
                        f"Error: {str(e)}"
                    ],
                    "recommendations": [
                        "Perform manual log analysis",
                        "Check NVIDIA NIM service availability",
                        "Review system connectivity and authentication"
                    ],
                    "next_steps": [
                        "Contact system administrator",
                        "Review raw log data manually"
                    ],
                    "confidence": "Low",
                    "analysis_method": "Fallback - Service Error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }


            # Step 5: Generate Markdown report with visualizations
            logger.info("📄 Step 5: Generating Markdown report with charts...")
            try:
                logger.info(f"📁 Report directory: {report_dir}")
                logger.info(f"📊 Final analysis_data type: {type(analysis_data)}")
                logger.info(f"🤖 Final nim_analysis type: {type(nim_analysis)}")
                
                # Call the actual Markdown generator
                report_files = await self.markdown_generator.generate_markdown_report(
                    analysis_data, nim_analysis, report_dir
                )
                
                # report_files should contain paths to markdown file and any generated images
                markdown_file = report_files.get("markdown_file")
                image_files = report_files.get("image_files", [])
                
                logger.info(f"✅ Markdown Report generated: {markdown_file}")
                if image_files:
                    logger.info(f"📊 Generated {len(image_files)} chart images")
                
                report_path = markdown_file
                
            except Exception as e:
                logger.error(f"❌ Markdown generation failed: {e}")
                logger.error(f"❌ Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                
                # Fallback to JSON report in the same directory
                report_path = os.path.join(report_dir, "fallback_analysis.json")
                
                with open(report_path, 'w') as f:
                    json.dump({
                        'analysis_data': analysis_data,
                        'nim_analysis': nim_analysis,
                        'generated_at': datetime.now().isoformat(),
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'analysis_data_type': str(type(analysis_data)),
                        'nim_analysis_type': str(type(nim_analysis))
                    }, f, indent=2)
                
                logger.info(f"✅ Fallback JSON report generated: {report_path}")


            
            # Step 6: Upload to OCI Object Storage (optional)
            logger.info("☁️ Step 6: Uploading report to OCI Object Storage...")
            upload_success = False
            try:
                if settings.OCI_NAMESPACE and settings.OCI_BUCKET_NAME:
                    # Upload main report file
                    with open(report_path, 'rb') as f:
                        report_content = f.read()
                    
                    report_filename = os.path.basename(report_path)
                    upload_success = await self.oci_client.upload_report(report_filename, report_content)
                    
                    # Also upload any generated images if they exist
                    if 'report_files' in locals() and report_files.get("image_files"):
                        for image_file in report_files["image_files"]:
                            try:
                                with open(image_file, 'rb') as f:
                                    image_content = f.read()
                                image_filename = os.path.basename(image_file)
                                await self.oci_client.upload_report(image_filename, image_content)
                                logger.info(f"✅ Uploaded image: {image_filename}")
                            except Exception as img_e:
                                logger.warning(f"⚠️ Failed to upload image {image_file}: {img_e}")
                    
                    if upload_success:
                        logger.info("✅ Report uploaded to OCI successfully")
                    else:
                        logger.info("ℹ️ Report upload to OCI failed or disabled")
                else:
                    logger.info("ℹ️ OCI upload skipped (not configured)")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to upload to OCI: {e}")
            
            # Analysis completed successfully
            analysis_duration = datetime.now() - analysis_start_time
            logger.info(f"🎉 Analysis completed successfully in {analysis_duration.total_seconds():.1f} seconds!")
            
            result = {
                "success": True,
                "report_path": report_path,
                "report_dir": report_dir,
                "uploaded_to_oci": upload_success,
                "timestamp": analysis_start_time.isoformat(),
                "duration_seconds": analysis_duration.total_seconds(),
                "connections": connections,
                "data_summary": {
                    "total_logs": stats.get("total_requests", 0),
                    "countries": stats.get("unique_countries", 0),
                    "protocols": stats.get("unique_sensors", 0),
                    "time_range": analysis_data.get("current_period", {}).get("time_range", "24h")
                },
                "analysis_method": "NVIDIA NIM" if settings.NVIDIA_NIM_API_KEY else "Fallback Analysis"
            }
            
            self.last_analysis_result = result
            return result
            
        except Exception as e:
            analysis_duration = datetime.now() - analysis_start_time
            error_msg = f"Analysis failed after {analysis_duration.total_seconds():.1f}s: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            result = {
                "success": False,
                "error": str(e),
                "timestamp": analysis_start_time.isoformat(),
                "duration_seconds": analysis_duration.total_seconds(),
                "report_dir": report_dir
            }
            
            self.last_analysis_result = result
            return result
        
        finally:
            # Clean up MCP connection
            try:
                await self.mcp_client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing MCP connection: {e}")
    
    def _get_default_analysis_prompt(self) -> str:
        """Get default analysis prompt"""
        return """
        Analyze the provided Oracle Cloud Infrastructure log data and provide a comprehensive security and traffic analysis report.
        
        Please include:
        
        1. **Executive Summary**
           - Key findings and overall security posture
           - Critical issues requiring immediate attention
        
        2. **Security Threat Assessment**
           - Potential security threats and vulnerabilities
           - Suspicious IP addresses or traffic patterns
           - Risk level assessment (Low/Medium/High/Critical)
        
        3. **Traffic Pattern Analysis**
           - Traffic volume trends and patterns
           - Peak usage times and geographic distribution
           - Protocol usage analysis
        
        4. **Geographic Analysis**
           - Traffic distribution by country/region
           - Unusual geographic access patterns
           - Recommendations for geo-blocking if needed
        
        5. **Anomaly Detection**
           - Unusual traffic spikes or patterns
           - Potential DDoS or brute force attempts
           - Outliers in normal traffic behavior
        
        6. **Recommendations**
           - Immediate actions required
           - Long-term security improvements
           - Monitoring and alerting suggestions
        
        7. **Action Items**
           - Prioritized list of security tasks
           - Timeline for implementation
        
        Focus on actionable insights and provide specific recommendations based on the data patterns observed.
        """
    
    def _generate_fallback_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback analysis when AI is not available"""
        stats = analysis_data.get("summary_statistics", {})
        country_data = analysis_data.get("country_analytics", {}).get("analytics", [])
        protocol_data = analysis_data.get("protocol_analytics", {}).get("analytics", [])
        
        total_logs = stats.get("total_logs", 0)
        total_bytes = stats.get("total_bytes", 0)
        
        # Basic analysis
        top_country = country_data[0]["country"] if country_data else "Unknown"
        top_protocol = protocol_data[0]["protocol"] if protocol_data else "Unknown"
        
        # Calculate some basic metrics
        avg_bytes_per_log = total_bytes / total_logs if total_logs > 0 else 0
        countries_count = len(country_data)
        protocols_count = len(protocol_data)
        
        return {
            "executive_summary": f"Analyzed {total_logs:,} log entries from Oracle Cloud Infrastructure over the past 24 hours. Traffic shows normal patterns with {countries_count} countries and {protocols_count} different protocols observed.",
            
            "key_findings": [
                f"Total log entries processed: {total_logs:,}",
                f"Total data volume: {total_bytes / (1024*1024):.1f} MB",
                f"Primary traffic source: {top_country}",
                f"Most used protocol: {top_protocol}",
                f"Geographic distribution: {countries_count} countries",
                f"Average bytes per request: {avg_bytes_per_log:.0f}"
            ],
            
            "security_analysis": f"Automated analysis of {total_logs:,} log entries completed. Traffic patterns appear within normal parameters. No obvious security anomalies detected in the current dataset, but manual review is recommended for comprehensive threat assessment.",
            
            "traffic_patterns": {
                "total_requests": total_logs,
                "total_bytes": total_bytes,
                "top_country": top_country,
                "top_protocol": top_protocol,
                "geographic_spread": countries_count,
                "protocol_diversity": protocols_count
            },
            
            "recommendations": [
                "Continue monitoring traffic patterns for unusual spikes or geographic anomalies",
                "Review top traffic sources for legitimacy and expected usage patterns",
                "Consider implementing automated alerting for traffic volume thresholds",
                "Regularly review protocol usage to ensure only necessary services are exposed",
                "Implement geographic access controls if traffic from unexpected regions is observed",
                "Schedule regular comprehensive security reviews of log data"
            ],
            
            "risk_level": "Medium",
            "confidence": "Medium (Automated Statistical Analysis)",
            "analysis_method": "Fallback statistical analysis - manual review recommended",
            "next_steps": [
                "Review detailed country and protocol breakdowns",
                "Investigate any unusual traffic patterns manually",
                "Consider enabling AI analysis with NVIDIA NIM for deeper insights"
            ]
        }
    
    def start_scheduler(self):
        """Start the scheduled analysis"""
        if self.is_running:
            logger.warning("⚠️ Scheduler is already running")
            return
        
        logger.info(f"🕐 Starting analysis scheduler...")
        logger.info(f"📅 Analysis will run every {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")
        
        # Schedule regular analysis - ONLY THIS ONE
        schedule.every(settings.ANALYSIS_INTERVAL_HOURS).hours.do(self._run_scheduled_analysis)
        
        # Run initial analysis after 2 minutes (not every minute!)
        schedule.every(2).minutes.do(self._run_initial_analysis).tag('initial')
        
        self.is_running = True
        self.scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Analysis scheduler started successfully")
        logger.info(f"🎯 Initial analysis will run in 2 minutes, then every {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")

    
    def stop_scheduler(self):
        """Stop the scheduled analysis"""
        if not self.is_running:
            logger.warning("⚠️ Scheduler is not running")
            return
            
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.info("🛑 Stopping scheduler thread...")
            # Thread will stop on next iteration due to is_running = False
        
        logger.info("✅ Analysis scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop running in separate thread"""
        logger.info("🔄 Scheduler loop started")
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                time.sleep(60)  # Continue after error
        
        logger.info("🔄 Scheduler loop ended")
    
    def _run_scheduled_analysis(self):
        """Wrapper for scheduled analysis"""
        logger.info("⏰ Scheduled analysis triggered")
        try:
            asyncio.run(self.run_analysis())
        except Exception as e:
            logger.error(f"❌ Scheduled analysis failed: {e}")
    
    def _run_initial_analysis(self):
        """Run initial analysis and remove the job"""
        logger.info("🎯 Running initial analysis...")
        try:
            asyncio.run(self.run_analysis())
        except Exception as e:
            logger.error(f"❌ Initial analysis failed: {e}")
        finally:
            # Remove the initial job so it doesn't repeat
            schedule.clear('initial')
            logger.info(f"📅 Initial analysis complete. Next analysis in {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")

    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        next_run = None
        if schedule.jobs:
            next_runs = [job.next_run for job in schedule.jobs if job.next_run]
            if next_runs:
                next_run = min(next_runs)
        
        # Test MCP connection for current status
        mcp_connected = False
        try:
            mcp_connected = await self.mcp_client.test_connection()
        except Exception as e:
            logger.debug(f"MCP connection test failed: {e}")
        
        status = {
            "is_running": self.is_running,
            "next_scheduled_run": next_run.isoformat() if next_run else None,
            "interval_hours": settings.ANALYSIS_INTERVAL_HOURS,
            "active_jobs": len(schedule.jobs),
            "mcp_server_script": settings.MCP_SERVER_SCRIPT_PATH,
            "mcp_connected": mcp_connected,
            "last_analysis": self.last_analysis_result,
            "scheduler_thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }
        
        return status
    
    async def run_manual_analysis(self) -> Dict[str, Any]:
        """Run analysis manually (triggered from web interface)"""
        logger.info("👤 Manual analysis triggered")
        return await self.run_analysis()
    
    async def cleanup(self):
        """Cleanup scheduler resources"""
        logger.info("🧹 Cleaning up scheduler resources...")
        
        # Stop scheduler
        self.stop_scheduler()
        
        # Close MCP connection
        try:
            await self.mcp_client.close()
        except Exception as e:
            logger.warning(f"⚠️ Error closing MCP client: {e}")
        
        # Close other clients if they have cleanup methods
        if hasattr(self.nim_client, 'close'):
            try:
                await self.nim_client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing NIM client: {e}")
        
        logger.info("✅ Scheduler cleanup completed")
