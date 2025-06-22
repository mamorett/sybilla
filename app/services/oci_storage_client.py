import oci
from typing import Optional
from app.config import settings

class OCIStorageClient:
    def __init__(self):
        self.config = oci.config.from_file(settings.OCI_CONFIG_FILE, settings.OCI_PROFILE)
        self.object_storage_client = oci.object_storage.ObjectStorageClient(self.config)
        self.namespace = settings.OCI_NAMESPACE
        self.bucket_name = settings.OCI_BUCKET_NAME
    
    async def get_analysis_prompt(self) -> str:
        """Get the analysis prompt from OCI Object Storage"""
        try:
            response = self.object_storage_client.get_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=settings.OCI_PROMPT_OBJECT_NAME
            )
            
            prompt_content = response.data.content.decode('utf-8')
            return prompt_content
            
        except Exception as e:
            print(f"Error reading prompt from OCI: {e}")
            # Return default prompt if file not found
            return self._get_default_prompt()
    
    async def upload_report(self, report_filename: str, report_content: bytes) -> bool:
        """Upload generated report to OCI Object Storage"""
        try:
            self.object_storage_client.put_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=f"reports/{report_filename}",
                put_object_body=report_content
            )
            return True
        except Exception as e:
            print(f"Error uploading report to OCI: {e}")
            return False
    
    def _get_default_prompt(self) -> str:
        """Default analysis prompt if none found in OCI"""
        return """
Analyze the provided Oracle Cloud Infrastructure logs and provide insights on:

1. SECURITY ANALYSIS:
   - Identify potential security threats or suspicious activities
   - Analyze traffic patterns for anomalies
   - Detect unusual geographic access patterns
   - Identify potential DDoS or brute force attacks

2. TRAFFIC ANALYSIS:
   - Analyze traffic volume and patterns
   - Identify peak usage times and geographic distribution
   - Sensor usage analysis
   - Bandwidth utilization patterns

3. OPERATIONAL INSIGHTS:
   - System performance indicators
   - Resource utilization patterns
   - Error rates and failure patterns
   - Capacity planning recommendations

4. RECOMMENDATIONS:
   - Security improvements
   - Performance optimizations
   - Cost optimization opportunities
   - Monitoring and alerting suggestions

Please provide specific metrics and data points that can be visualized in charts and graphs.
"""
