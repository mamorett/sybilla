import oci
from typing import Optional, Union
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class OCIStorageClient:
    def __init__(self):
        try:
            config, signer = self._get_oci_auth()
            self.object_storage_client = oci.object_storage.ObjectStorageClient(config, signer=signer)
            self.namespace = settings.OCI_NAMESPACE
            self.bucket_name = settings.OCI_BUCKET_NAME
            auth_method = "Instance Principals" if signer else "Config File"
            logger.info(f"✅ OCI Storage Client initialized successfully using {auth_method}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OCI Storage Client: {e}")
            if not settings.OCI_NAMESPACE or not settings.OCI_BUCKET_NAME:
                logger.info("ℹ️ OCI Storage not configured, client will be non-functional.")
                self.object_storage_client = None
                self.namespace = None
                self.bucket_name = None
            else:
                raise

    def _get_oci_auth(self) -> tuple[dict, Optional[oci.auth.signers.InstancePrincipalsSecurityTokenSigner]]:
        """Get OCI configuration and signer, with fallback from config file to instance principals"""
        try:
            config = oci.config.from_file(settings.OCI_CONFIG_FILE, settings.OCI_PROFILE)
            logger.info("🔑 OCI Storage: Using OCI config file authentication")
            return config, None
        except Exception as config_error:
            logger.warning(f"⚠️ OCI Storage: Config file authentication failed: {config_error}")
            try:
                signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
                config = {'region': signer.region}
                logger.info("🔑 OCI Storage: Using Instance Principals authentication")
                return config, signer
            except Exception as instance_error:
                logger.error(f"❌ OCI Storage: Instance Principals authentication failed: {instance_error}")
                raise Exception(
                    f"OCI Storage: Both authentication methods failed. "
                    f"Config file error: {config_error}. "
                    f"Instance principals error: {instance_error}"
                )
    
    async def get_analysis_prompt(self) -> str:
        """Get the analysis prompt from OCI Object Storage"""
        if not self.object_storage_client or not self.bucket_name:
            logger.info("OCI client not available, returning default prompt.")
            return self._get_default_prompt()
        try:
            response = self.object_storage_client.get_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=settings.OCI_PROMPT_OBJECT_NAME
            )
            
            prompt_content = response.data.content.decode('utf-8')
            return prompt_content
            
        except Exception as e:
            logger.error(f"Error reading prompt from OCI: {e}")
            # Return default prompt if file not found
            return self._get_default_prompt()
    
    async def upload_report(self, report_filename: str, report_content: bytes) -> bool:
        """Upload generated report to OCI Object Storage"""
        if not self.object_storage_client or not self.bucket_name:
            logger.info("OCI client not available, skipping upload.")
            return False
        try:
            self.object_storage_client.put_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=f"reports/{report_filename}",
                put_object_body=report_content
            )
            return True
        except Exception as e:
            logger.error(f"Error uploading report to OCI: {e}")
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
