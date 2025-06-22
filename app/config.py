import os
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MCP Server
    MCP_SERVER_URL: str = "http://localhost:8000"
    
    # NVIDIA NIM
    NVIDIA_NIM_API_KEY: str
    NVIDIA_NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "meta/llama-3.1-405b-instruct"
    
    # OCI Object Storage
    OCI_CONFIG_FILE: str = "~/.oci/config"
    OCI_PROFILE: str = "DEFAULT"
    OCI_NAMESPACE: str
    OCI_BUCKET_NAME: str
    OCI_PROMPT_OBJECT_NAME: str = "analysis_prompt.txt"
    
    # Scheduler
    ANALYSIS_INTERVAL_HOURS: int = 1
    REPORT_OUTPUT_DIR: str = "reports"
    
    # Database (optional for storing analysis history)
    DATABASE_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()
