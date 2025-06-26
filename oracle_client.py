import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import oci
from oci.logging import LoggingManagementClient
from oci.loggingsearch import LogSearchClient
from oci.loggingsearch.models import SearchLogsDetails

# Simple import
from models import LogEntry

class OracleLogsClient:
    def __init__(self):
        """Initialize Oracle Cloud connection with support for both config file and instance principals"""
        try:
            # Try to initialize Oracle Cloud clients with fallback authentication
            self.config, self.signer = self._get_oci_auth()
            
            # Retrieve Oracle Cloud identifiers from environment variables
            self.compartment_id = os.getenv("OCI_COMPARTMENT_ID")
            self.log_group_id = os.getenv("OCI_LOG_GROUP_ID")
            self.log_id = os.getenv("OCI_LOG_ID")

            if not all([self.compartment_id, self.log_group_id, self.log_id]):
                raise ValueError(
                    "Missing one or more required Oracle Cloud environment variables: "
                    "OCI_COMPARTMENT_ID, OCI_LOG_GROUP_ID, OCI_LOG_ID"
                )

            # Initialize OCI clients after config and IDs are loaded
            self.logging_client = LoggingManagementClient(self.config, signer=self.signer)
            self.search_client = LogSearchClient(self.config, signer=self.signer)
            
            auth_method = "Instance Principals" if self.signer else "Config File"
            print(f"✅ Oracle Cloud connection initialized successfully using {auth_method}")
            print(f"📋 Targeting Compartment: {self.compartment_id}")
            print(f"📋 Targeting Log Group: {self.log_group_id}")
            print(f"📋 Targeting Log: {self.log_id}")
            
        except Exception as e:
            print(f"❌ Failed to initialize Oracle Cloud connection: {e}")
            raise

    def _get_oci_auth(self) -> tuple[dict, oci.auth.signers.BaseSigner | None]:
        """Get OCI configuration and signer, with fallback from config file to instance principals"""
        try:
            # First, try to load from config file
            config = oci.config.from_file()
            print("🔑 Using OCI config file authentication")
            return config, None
        except Exception as config_error:
            print(f"⚠️ Config file authentication failed: {config_error}")
            try:
                # Fallback to instance principals
                signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
                config = {'region': signer.region}
                print("🔑 Using Instance Principals authentication")
                return config, signer
            except Exception as instance_error:
                print(f"❌ Instance Principals authentication failed: {instance_error}")
                raise Exception(
                    f"Both authentication methods failed. "
                    f"Config file error: {config_error}. "
                    f"Instance principals error: {instance_error}"
                )

    
    def _build_base_query(self) -> str:
        """Build the base query targeting the specific log"""
        return f'search "{self.compartment_id}/{self.log_group_id}/{self.log_id}"'
    
    def _build_country_query(self, params: Dict[str, Any]) -> str:
        base_query = self._build_base_query()
        conditions = []
        
        if params.get('country'):
            conditions.append(f"data.Country = '{params['country']}'")
        
        if params.get('country_code'):
            conditions.append(f"data.CountryCode = '{params['country_code']}'")
        
        if conditions:
            base_query += ' | where ' + ' and '.join(conditions)
        
        if params.get('limit'):
            base_query += f" | limit {params['limit']}"
            
        return base_query

    def _build_location_query(self, params: Dict[str, Any]) -> str:
        query = self._build_base_query()
        query += f" | where data.Latitude >= {params['lat_min']} and data.Latitude <= {params['lat_max']}"
        query += f" | where data.Longitude >= {params['lon_min']} and data.Longitude <= {params['lon_max']}"
        
        if params.get('limit'):
            query += f" | limit {params['limit']}"
            
        return query
    
    def _build_ip_query(self, params: Dict[str, Any]) -> str:
        query = self._build_base_query()
        
        if params.get('ip_address'):
            # Exact IP match
            query += f" | where data.IP = '{params['ip_address']}'"
        elif params.get('ip_range'):
            ip_range = params['ip_range']
            
            # For IP ranges, especially 0.0.0.0/0, just get all logs
            # We'll filter in Python if needed
            if ip_range == "0.0.0.0/0":
                print("🔍 Getting all logs for IP analysis")
                # No additional filter - get all logs
            else:
                print(f"🔍 Getting all logs for IP range {ip_range} - will filter in Python")
                # No additional filter - get all logs
        
        if params.get('limit'):
            query += f" | limit {params['limit']}"
            
        return query


    def _build_sensor_query(self, sensor: str, params: Dict[str, Any]) -> str:
        query = self._build_base_query()
        query += f" | where data.Sensor = '{sensor}'"
        
        if params.get('limit'):
            query += f" | limit {params['limit']}"
            
        return query

    def _build_isp_query(self, isp: str, params: Dict[str, Any]) -> str:
        query = self._build_base_query()
        query += f" | where data.ISP = '{isp}'"
        
        if params.get('limit'):
            query += f" | limit {params['limit']}"
            
        return query

    async def _execute_oracle_query(
        self, 
        query: str, 
        start_time: datetime, 
        end_time: datetime, 
        max_results: int = None
    ) -> List[Dict]:
        """Execute the actual Oracle Cloud Logging query with pagination support"""
        try:
            print(f"🔍 Executing query: {query}")
            print(f"📅 Time range: {start_time} to {end_time}")

            search_details = SearchLogsDetails(
                time_start=start_time,
                time_end=end_time,
                search_query=query,
                is_return_field_info=False
            )

            all_logs = []
            next_page = None

            while True:
                response = self.search_client.search_logs(
                    search_logs_details=search_details,
                    page=next_page
                )

                for result in response.data.results:
                    try:
                        log_data = json.loads(result.data) if isinstance(result.data, str) else result.data
                        all_logs.append(log_data)
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse log JSON: {e}")
                        continue

                # Pagination: get next page token
                next_page = response.headers.get('opc-next-page')
                if not next_page:
                    break

                # Stop if we've reached max_results
                if max_results and len(all_logs) >= max_results:
                    all_logs = all_logs[:max_results]
                    break

            print(f"✅ Found {len(all_logs)} log entries (with pagination)")
            return all_logs

        except Exception as e:
            print(f"❌ Error executing Oracle query: {e}")
            return []

    def _parse_oracle_log_entry(self, oracle_log: Dict) -> LogEntry:
        """Parse Oracle log JSON into LogEntry model"""
        try:
            log_content = oracle_log.get('logContent', {})
            data = log_content.get('data', {})
            
            # Convert timestamp - Oracle gives milliseconds since epoch
            timestamp_ms = oracle_log.get('datetime', 0)
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)
            
            return LogEntry(
                timestamp=timestamp,
                ip=data.get('IP', ''),
                sensor=data.get('Sensor', ''),
                latitude=float(data.get('Latitude', 0.0)),
                longitude=float(data.get('Longitude', 0.0)),
                country=data.get('Country', ''),
                country_code=data.get('CountryCode', ''),
                city=data.get('City', ''),
                isp=data.get('ISP', '')
            )
            
        except Exception as e:
            print(f"Error parsing log entry: {e}")
            return None

    async def search_logs_by_country(self, params: Dict[str, Any]) -> List[LogEntry]:
        """Search logs by country or country code"""
        start_time, end_time = self._parse_time_range(params.get('time_range', '24h'))
        query = self._build_country_query(params)
        max_results = params.get('max_results')

        oracle_logs = await self._execute_oracle_query(query, start_time, end_time, max_results=max_results)
        
        log_entries = []
        for oracle_log in oracle_logs:
            entry = self._parse_oracle_log_entry(oracle_log)
            if entry:
                log_entries.append(entry)
        
        return log_entries

    async def search_logs_by_location(self, params: Dict[str, Any]) -> List[LogEntry]:
        """Search logs within geographic bounds"""
        start_time, end_time = self._parse_time_range(params.get('time_range', '24h'))
        query = self._build_location_query(params)
        max_results = params.get('max_results')

        oracle_logs = await self._execute_oracle_query(query, start_time, end_time, max_results=max_results)
        
        log_entries = []
        for oracle_log in oracle_logs:
            entry = self._parse_oracle_log_entry(oracle_log)
            if entry:
                log_entries.append(entry)
        
        return log_entries

    async def search_logs_by_ip(self, params: Dict[str, Any]) -> List[LogEntry]:
        """Search logs by IP address or range"""
        start_time, end_time = self._parse_time_range(params.get('time_range', '24h'))
        query = self._build_ip_query(params)
        max_results = params.get('max_results')

        oracle_logs = await self._execute_oracle_query(query, start_time, end_time, max_results=max_results)
        
        log_entries = []
        for oracle_log in oracle_logs:
            entry = self._parse_oracle_log_entry(oracle_log)
            if entry:
                log_entries.append(entry)
        
        return log_entries


    def _process_analytics(self, oracle_logs: List[Dict], group_by: str) -> Dict[str, Any]:
        """Process logs into analytics summary"""
        from collections import Counter
        
        unique_ips = set()
        grouped_data = []
        sensors = []
        countries = []
        cities = []
        isps = []
        
        for oracle_log in oracle_logs:
            try:
                data = oracle_log.get('logContent', {}).get('data', {})
                
                unique_ips.add(data.get('IP', ''))
                sensors.append(data.get('Sensor', ''))
                countries.append(data.get('Country', ''))
                cities.append(data.get('City', ''))
                isps.append(data.get('ISP', ''))
                
                # Group by requested field
                if group_by == 'country':
                    grouped_data.append(data.get('Country', 'Unknown'))
                elif group_by == 'city':
                    grouped_data.append(f"{data.get('City', 'Unknown')}, {data.get('Country', '')}")
                elif group_by == 'isp':
                    grouped_data.append(data.get('ISP', 'Unknown'))
                elif group_by == 'sensor':
                    grouped_data.append(data.get('Sensor', 'Unknown'))
                    
            except Exception as e:
                print(f"Error processing log for analytics: {e}")
                continue
        
        grouped_counter = Counter(grouped_data)
        sensor_counter = Counter(sensors)
        
        return {
            'unique_ips': len(unique_ips),
            'unique_countries': len(set(countries)),
            'unique_cities': len(set(cities)),
            f'top_{group_by}': [
                {'name': item, 'count': count} 
                for item, count in grouped_counter.most_common(10)
            ],
            'sensor_distribution': dict(sensor_counter.most_common()),
            'top_isps': [isp for isp, _ in Counter(isps).most_common(5)]
        }
    
    def _parse_time_range(self, time_range: str) -> tuple[datetime, datetime]:
        """Parse time range string like '24h', '7d', '1w' into datetime objects"""
        now = datetime.utcnow()
        
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = now - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = now - timedelta(days=days)
        elif time_range.endswith('w'):
            weeks = int(time_range[:-1])
            start_time = now - timedelta(weeks=weeks)
        else:
            start_time = now - timedelta(hours=24)
            
        return start_time, now

    async def get_traffic_analytics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get aggregated traffic statistics"""
        
        # ADD DEBUG LOGGING
        print(f"🔍 ORACLE CLIENT DEBUG:")
        print(f"  Arguments received: {params}")
        print(f"  Arguments type: {type(params)}")
        print(f"  Time range: {params.get('time_range', 'NOT FOUND')}")
        print(f"  Group by: {params.get('group_by', 'NOT FOUND')}")
        print(f"  Limit: {params.get('limit', 'NOT FOUND')}")
        
        start_time, end_time = self._parse_time_range(params.get('time_range', '24h'))
        base_query = self._build_base_query()
        if params.get('limit'):
            base_query += f' | limit {params["limit"] * 10}'  # Get more for analytics
        max_results = params.get('max_results')

        # ADD DEBUG LOGGING
        print(f"🔍 ORACLE QUERY DEBUG:")
        print(f"  Final query: {base_query}")
        print(f"  Start time: {start_time}")
        print(f"  End time: {end_time}")

        oracle_logs = await self._execute_oracle_query(base_query, start_time, end_time, max_results=max_results)
        
        # ADD DEBUG LOGGING
        print(f"🔍 ORACLE RESULTS DEBUG:")
        print(f"  Raw logs returned: {len(oracle_logs)}")
        if oracle_logs:
            print(f"  First log structure: {list(oracle_logs[0].keys())}")
            print(f"  First log sample: {oracle_logs[0]}")
        
        analytics = self._process_analytics(oracle_logs, params.get('group_by', 'country'))
        analytics['time_range'] = params.get('time_range', '24h')
        analytics['total_requests'] = len(oracle_logs)
        analytics['log_source'] = self.log_id
        analytics['query_used'] = base_query  # For debugging
        
        return analytics



    def _process_analytics(self, oracle_logs: List[Dict], group_by: str) -> Dict[str, Any]:
        """Enhanced analytics processing with better grouping"""
        from collections import Counter
        
        unique_ips = set()
        grouped_data = []
        sensors = []
        countries = []
        cities = []
        isps = []
        
        print(f"🔍 Processing {len(oracle_logs)} logs for group_by: {group_by}")
        
        for oracle_log in oracle_logs:
            try:
                # Handle different log structures
                if 'logContent' in oracle_log:
                    data = oracle_log.get('logContent', {}).get('data', {})
                else:
                    # Direct data structure
                    data = oracle_log.get('data', oracle_log)
                
                ip = data.get('IP', '')
                sensor = data.get('Sensor', '')
                country = data.get('Country', '')
                city = data.get('City', '')
                isp = data.get('ISP', '')
                
                if ip:
                    unique_ips.add(ip)
                if sensor:
                    sensors.append(sensor)
                if country:
                    countries.append(country)
                if city:
                    cities.append(city)
                if isp:
                    isps.append(isp)
                
                # Group by requested field
                if group_by == 'country' and country:
                    grouped_data.append(country)
                elif group_by == 'city' and city:
                    grouped_data.append(f"{city}, {country}" if country else city)
                elif group_by == 'isp' and isp:
                    grouped_data.append(isp)
                elif group_by == 'sensor' and sensor:
                    grouped_data.append(sensor)
                    
            except Exception as e:
                print(f"Error processing log for analytics: {e}")
                continue
        
        grouped_counter = Counter(grouped_data)
        sensor_counter = Counter([s for s in sensors if s])
        country_counter = Counter([c for c in countries if c])
        city_counter = Counter([c for c in cities if c])
        isp_counter = Counter([i for i in isps if i])
        
        print(f"🔍 Grouped data counts: {len(grouped_data)} items")
        print(f"🔍 Top 3 {group_by}: {grouped_counter.most_common(3)}")
        
        return {
            'unique_ips': len(unique_ips),
            'unique_countries': len(set([c for c in countries if c])),
            'unique_cities': len(set([c for c in cities if c])),
            'unique_sensors': len(set([s for s in sensors if s])),
            'unique_isps': len(set([i for i in isps if i])),
            f'top_{group_by}': [
                {'name': item, 'count': count} 
                for item, count in grouped_counter.most_common(10)
            ],
            'sensor_distribution': dict(sensor_counter.most_common()),
            'country_distribution': dict(country_counter.most_common()),
            'city_distribution': dict(city_counter.most_common(10)),
            'isp_distribution': dict(isp_counter.most_common(10)),
            'raw_counts': {
                'total_logs': len(oracle_logs),
                'grouped_items': len(grouped_data),
                'sensors': len(sensors),
                'countries': len(countries),
                'cities': len(cities),
                'isps': len(isps)
            }
        }

    # Add method for multiple countries
    async def search_logs_by_countries(self, params: Dict[str, Any]) -> List[LogEntry]:
        """Search logs by multiple countries"""
        countries = params.get('countries', [])
        if not countries:
            return []
        
        start_time, end_time = self._parse_time_range(params.get('time_range', '24h'))
        
        # Build query for multiple countries
        base_query = self._build_base_query()
        country_conditions = [f"data.Country = '{country.strip()}'" for country in countries]
        base_query += ' | where ' + ' or '.join(country_conditions)
        
        if params.get('limit'):
            base_query += f" | limit {params['limit']}"
        
        max_results = params.get('max_results')
        oracle_logs = await self._execute_oracle_query(base_query, start_time, end_time, max_results=max_results)
        
        log_entries = []
        for oracle_log in oracle_logs:
            entry = self._parse_oracle_log_entry(oracle_log)
            if entry:
                log_entries.append(entry)
        
        return log_entries
