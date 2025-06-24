Oracle Logs Analysis Frontend
=============================

This project provides a comprehensive web-based frontend for automated analysis of Oracle Cloud Infrastructure (OCI) logs. It integrates with an Oracle Logs MCP (Management and Control Plane) server to gather log data, leverages NVIDIA NIM for advanced AI-driven security and performance analysis, and generates detailed Markdown reports with visualizations. Reports can optionally be uploaded to OCI Object Storage for persistent storage.

Features
--------

-   **Automated Log Data Gathering**: Connects to an Oracle Logs MCP server to retrieve multi-dimensional log data, including traffic analytics by country, city, sensor, ISP, and detailed IP analytics.
-   **AI-Powered Analysis (NVIDIA NIM)**: Utilizes NVIDIA NIM to perform in-depth security and performance assessments of the gathered log data, identifying anomalies, threats, and providing actionable insights.
-   **Comprehensive Markdown Reports**: Generates rich Markdown reports that include key metrics, visual analytics (charts for traffic distribution, IP patterns, etc.), security assessments, key findings, and recommendations.
-   **OCI Integration**: Seamlessly uploads generated reports and associated images to OCI Object Storage for secure and scalable archival.
-   **Web Dashboard**: Provides an intuitive web interface to monitor scheduler status, manually trigger analyses, and view historical analysis reports.
-   **Scheduled Analysis**: Configurable scheduler to automatically run analyses at specified intervals.

Architecture Overview
---------------------

The application is built using FastAPI and follows a modular design:

-   **`app/main.py`**: The FastAPI application entry point, handling web routes, serving the dashboard, and managing the application lifecycle.
-   **`app/scheduler.py`**: Orchestrates the analysis process, including fetching data, invoking AI analysis, generating reports, and managing the scheduling of these tasks.
-   **`app/services/analytics_services.py`**: Responsible for preparing and processing log data, including fetching various types of analytics (country, sensor, IP, etc.) from the MCP server.
-   **`app/services/mcp_client.py`**: Handles communication with the Oracle Logs MCP server using a JSON-RPC like protocol to retrieve log data.
-   **`app/services/nvidia_nim_client.py`**: Interfaces with the NVIDIA NIM API to send log data for AI-driven analysis and receive structured insights.
-   **`app/services/oci_storage_client.py`**: Manages interactions with Oracle Cloud Infrastructure Object Storage for uploading reports and other files.
-   **`app/services/markdown_generator.py`**: Generates the detailed Markdown reports, including creating various charts and integrating AI analysis results.
-   **`app/config.py`**: Manages application settings and environment variables.
-   **`templates/`**: Contains Jinja2 templates for the web dashboard and report viewer.
-   **`static/`**: Serves static assets like CSS and JavaScript.

Setup and Installation
----------------------

### Prerequisites

-   Python 3.8+
-   An operational Oracle Logs MCP server (its `server.py` script path is required).
-   (Optional) NVIDIA NIM API Key for AI analysis.
-   (Optional) OCI credentials configured for Object Storage access.

### 1. Clone the Repository

```bash
git clone <repository_url>
cd oracle-logs-analysis-frontend
```

### 2. Install Dependencies

It's recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory of the project or set these variables in your environment.

```ini
# Required: Path to your Oracle Logs MCP server script
MCP_SERVER_SCRIPT_PATH=/path/to/your/mcp/server.py

# Optional: NVIDIA NIM API Key for AI analysis
# If not provided, a fallback statistical analysis will be used.
NVIDIA_NIM_API_KEY=your_nvidia_nim_api_key

# Optional: OCI Object Storage Configuration
# If not provided, reports will only be stored locally.
OCI_NAMESPACE=your_oci_namespace
OCI_BUCKET_NAME=your_oci_bucket_name

# Optional: Countries to target for specific analysis (comma-separated)
ANALYTICS_COUNTRIES=IR,UA,BH,CY,EG,IQ,JO,KW,LB,OM,PS,QA,SA,SY,TR,AE,YE

# Analysis interval in hours (default: 24)
ANALYSIS_INTERVAL_HOURS=24
```

### 4. Run the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9090 --reload
```

The `--reload` flag is useful for development as it restarts the server on code changes. For production, remove it.

Usage
-----

Once the application is running, open your web browser and navigate to `http://localhost:9090`.

-   **Dashboard**: The main page displays the scheduler status and a list of past analysis runs.
-   **Trigger Analysis**: Use the "Run Analysis Now" button to manually initiate an analysis cycle.
-   **Scheduler Control**: Start or stop the automated analysis scheduler.
-   **View Reports**: Click "View Report" next to any completed analysis run to see the detailed Markdown report in your browser.

Configuration
-------------

The application's behavior can be customized via environment variables:

-   `MCP_SERVER_SCRIPT_PATH`: **Crucial**. This must point to the executable script of your Oracle Logs MCP server. The application communicates with this script to fetch log data.
-   `NVIDIA_NIM_API_KEY`: Your API key for NVIDIA NIM. This enables the advanced AI analysis capabilities. Without it, the system will perform basic statistical analysis.
-   `OCI_NAMESPACE`, `OCI_BUCKET_NAME`: Your Oracle Cloud Infrastructure Object Storage namespace and bucket name. Used for uploading generated reports. Ensure your OCI environment is configured with appropriate credentials (e.g., via `~/.oci/config` or instance principal).
-   `ANALYTICS_COUNTRIES`: A comma-separated list of country codes (e.g., `US,CA,GB`) for which the `AnalyticsService` will perform specific targeted log searches.
-   `ANALYSIS_INTERVAL_HOURS`: The frequency (in hours) at which the scheduler will automatically run a new analysis.

Contributing
------------

Contributions are welcome! Please feel free to submit issues or pull requests.

License
-------

This project is licensed under the MIT License.

```