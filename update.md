"""
Simple Utility Module for Glue DQDL Ruleset Sync

Four simple functions:
1. fetch_ruleset - Fetch all rulesets from AWS Glue
2. fetch_glue_metadata - Fetch Glue table metadata
3. format_metadata - Format metadata for database
4. upsert_data - Upsert data into PostgreSQL table

Main function: sync_glue_dqdl_ruleset_details
"""

import boto3
from psycopg2.extras import Json, execute_batch
from typing import Any, Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration constants
DEFAULT_MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "10"))  # Parallel processing threads
DEFAULT_BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "250"))  # Database batch insert size

# AWS Glue client (lazy initialization)
_glue_client = None


def get_glue_client(region_name: str):
    """Get AWS Glue client with lazy initialization"""
    global _glue_client
    if _glue_client is None:
        _glue_client = boto3.client("glue", region_name=region_name)
    return _glue_client


# ============================================================================
# FOUR SIMPLE FUNCTIONS
# ============================================================================

def _fetch_single_ruleset_detail(glue_client, ruleset_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single ruleset detail (helper for parallel processing).
    
    Args:
        glue_client: AWS Glue client
        ruleset_name: Name of the ruleset
        
    Returns:
        Ruleset detail dictionary or None if failed
    """
    try:
        ruleset_detail = glue_client.get_data_quality_ruleset(Name=ruleset_name)
        logger.debug(f"Fetched ruleset details for: {ruleset_name}")
        return ruleset_detail
    except Exception as e:
        logger.warning(f"Failed to fetch ruleset details for {ruleset_name}: {str(e)}")
        return None


def fetch_ruleset(glue_client, max_workers: int = DEFAULT_MAX_WORKERS) -> List[Dict[str, Any]]:
    """
    Fetch all Data Quality rulesets from AWS Glue with parallel processing.
    
    Args:
        glue_client: AWS Glue client
        max_workers: Maximum number of parallel threads for fetching ruleset details
        
    Returns:
        List of ruleset dictionaries with full details
    """
    try:
        logger.info("Fetching all rulesets from Glue")
        ruleset_names = []
        next_token = None
        max_results = 100
        
        # Manual pagination since list_data_quality_rulesets doesn't support boto3 paginator
        while True:
            # Prepare request parameters
            request_params = {
                'MaxResults': max_results
            }
            if next_token:
                request_params['NextToken'] = next_token
            
            # Call the API
            response = glue_client.list_data_quality_rulesets(**request_params)
            
            # Collect ruleset names for parallel processing
            for ruleset in response.get("Rulesets", []):
                ruleset_names.append(ruleset["Name"])
            
            # Check if there are more results
            next_token = response.get("NextToken")
            if not next_token:
                break
        
        logger.info(f"Found {len(ruleset_names)} rulesets, fetching details in parallel (max_workers={max_workers})")
        
        # OPTIMIZATION 1: Parallel fetching of ruleset details
        rulesets = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_name = {
                executor.submit(_fetch_single_ruleset_detail, glue_client, name): name
                for name in ruleset_names
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_name):
                ruleset_name = future_to_name[future]
                try:
                    result = future.result()
                    if result:
                        rulesets.append(result)
                except Exception as e:
                    logger.warning(f"Exception while fetching ruleset {ruleset_name}: {str(e)}")
        
        logger.info(f"Fetched {len(rulesets)} rulesets from Glue (out of {len(ruleset_names)} total)")
        return rulesets
    except Exception as e:
        logger.error(f"Failed to fetch rulesets: {str(e)}")
        return []


def fetch_glue_metadata(glue_client, database_name: str, table_name: str) -> Dict[str, Any]:
    """
    Fetch Glue table metadata.
    
    Args:
        glue_client: AWS Glue client
        database_name: Name of the Glue database
        table_name: Name of the Glue table
        
    Returns:
        Table metadata dictionary
    """
    try:
        logger.debug(f"Fetching metadata for table: {database_name}.{table_name}")
        response = glue_client.get_table(DatabaseName=database_name, Name=table_name)
        table = response.get("Table", {})
        logger.debug(f"Fetched metadata for table: {database_name}.{table_name}")
        return table
    except Exception as e:
        logger.error(f"Failed to fetch metadata for {database_name}.{table_name}: {str(e)}")
        raise


def format_metadata(table: Dict[str, Any], ruleset: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format metadata for database insertion.
    
    Args:
        table: Glue table metadata dictionary
        ruleset: Optional ruleset metadata dictionary
        
    Returns:
        Formatted metadata dictionary ready for database
    """
    storage_descriptor = table.get("StorageDescriptor", {})
    serde_info = storage_descriptor.get("SerdeInfo", {})
    
    formatted = {
        "database_name": table.get("DatabaseName", ""),
        "table_name": table.get("Name", ""),
        "table_type": table.get("TableType"),
        "storage_location": storage_descriptor.get("Location"),
        "input_format": storage_descriptor.get("InputFormat"),
        "output_format": storage_descriptor.get("OutputFormat"),
        "serde_library": serde_info.get("SerializationLibrary"),
        "serde_parameters": serde_info.get("Parameters", {}),
        "columns_metadata": storage_descriptor.get("Columns", []),
        "partition_keys_metadata": table.get("PartitionKeys", []),
        "connection_name": table.get("TargetTable", {}).get("ConnectionName"),
        "parameters": table.get("Parameters", {}),
        "ruleset_name": ruleset.get("Name", "") if ruleset else "",
        "ruleset_description": ruleset.get("Description") if ruleset else None,
        "ruleset_dqdl": ruleset.get("Ruleset") if ruleset else None,
        "ruleset_created": ruleset.get("CreatedOn") if ruleset else None,
        "ruleset_modified": ruleset.get("LastModifiedOn") if ruleset else None
    }
    
    return formatted


def _prepare_upsert_data(metadata: Dict[str, Any]) -> Tuple:
    """
    Prepare metadata tuple for batch upsert.
    
    Args:
        metadata: Formatted metadata dictionary
        
    Returns:
        Tuple of values for database insertion
    """
    return (
        metadata["database_name"],
        metadata["table_name"],
        metadata["table_type"],
        metadata["storage_location"],
        metadata["input_format"],
        metadata["output_format"],
        metadata["serde_library"],
        Json(metadata["serde_parameters"]),
        Json(metadata["columns_metadata"]),
        Json(metadata["partition_keys_metadata"]),
        metadata["connection_name"],
        Json(metadata["parameters"]),
        metadata["ruleset_name"],
        metadata["ruleset_description"],
        metadata["ruleset_dqdl"],
        metadata["ruleset_created"],
        metadata["ruleset_modified"],
        'system'
    )


def batch_upsert_data(conn, schema_name: str, target_table: str, metadata_list: List[Dict[str, Any]], batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    """
    Batch upsert data into PostgreSQL table (OPTIMIZATION 2: Batch database operations).
    
    Args:
        conn: psycopg2 database connection
        schema_name: Database schema name
        target_table: Target table name
        metadata_list: List of formatted metadata dictionaries
        batch_size: Number of records to insert per batch
        
    Returns:
        Number of records successfully upserted
    """
    if not metadata_list:
        return 0
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        # Build WHERE clause to check if any field has changed
        # This ensures we only update when there's an actual change
        # In ON CONFLICT DO UPDATE, reference existing row using just column name (no table prefix needed)
        # Use jsonb comparison for JSON fields to handle ordering and whitespace differences properly
        # COALESCE handles NULL values by treating them as empty objects/arrays for comparison
        where_conditions = [
            "glue_catalog_table_type IS DISTINCT FROM EXCLUDED.glue_catalog_table_type",
            "glue_catalog_table_storage_location IS DISTINCT FROM EXCLUDED.glue_catalog_table_storage_location",
            "glue_catalog_table_input_format IS DISTINCT FROM EXCLUDED.glue_catalog_table_input_format",
            "glue_catalog_table_output_format IS DISTINCT FROM EXCLUDED.glue_catalog_table_output_format",
            "glue_catalog_table_serde_library IS DISTINCT FROM EXCLUDED.glue_catalog_table_serde_library",
            "COALESCE(glue_catalog_table_serde_parameters::jsonb, '{}'::jsonb) IS DISTINCT FROM COALESCE(EXCLUDED.glue_catalog_table_serde_parameters::jsonb, '{}'::jsonb)",
            "COALESCE(glue_catalog_table_columns_metadata::jsonb, '[]'::jsonb) IS DISTINCT FROM COALESCE(EXCLUDED.glue_catalog_table_columns_metadata::jsonb, '[]'::jsonb)",
            "COALESCE(glue_catalog_table_partition_keys_metadata::jsonb, '[]'::jsonb) IS DISTINCT FROM COALESCE(EXCLUDED.glue_catalog_table_partition_keys_metadata::jsonb, '[]'::jsonb)",
            "glue_catalog_table_connection_name IS DISTINCT FROM EXCLUDED.glue_catalog_table_connection_name",
            "COALESCE(glue_catalog_table_parameters::jsonb, '{}'::jsonb) IS DISTINCT FROM COALESCE(EXCLUDED.glue_catalog_table_parameters::jsonb, '{}'::jsonb)",
            "glue_dq_ruleset_description IS DISTINCT FROM EXCLUDED.glue_dq_ruleset_description",
            "glue_dq_ruleset_dqdl_rules IS DISTINCT FROM EXCLUDED.glue_dq_ruleset_dqdl_rules",
            "glue_dq_ruleset_created_timestamp IS DISTINCT FROM EXCLUDED.glue_dq_ruleset_created_timestamp",
            "glue_dq_ruleset_last_modified_timestamp IS DISTINCT FROM EXCLUDED.glue_dq_ruleset_last_modified_timestamp"
        ]
        where_clause = " OR ".join(where_conditions)
        
        upsert_query = f"""
            INSERT INTO {schema_name}.{target_table} (
                glue_catalog_database_name,
                glue_catalog_table_name,
                glue_catalog_table_type,
                glue_catalog_table_storage_location,
                glue_catalog_table_input_format,
                glue_catalog_table_output_format,
                glue_catalog_table_serde_library,
                glue_catalog_table_serde_parameters,
                glue_catalog_table_columns_metadata,
                glue_catalog_table_partition_keys_metadata,
                glue_catalog_table_connection_name,
                glue_catalog_table_parameters,
                glue_dq_ruleset_name,
                glue_dq_ruleset_description,
                glue_dq_ruleset_dqdl_rules,
                glue_dq_ruleset_created_timestamp,
                glue_dq_ruleset_last_modified_timestamp,
                created_by
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (glue_catalog_database_name, glue_catalog_table_name, glue_dq_ruleset_name)
            DO UPDATE SET
                glue_catalog_table_type = EXCLUDED.glue_catalog_table_type,
                glue_catalog_table_storage_location = EXCLUDED.glue_catalog_table_storage_location,
                glue_catalog_table_input_format = EXCLUDED.glue_catalog_table_input_format,
                glue_catalog_table_output_format = EXCLUDED.glue_catalog_table_output_format,
                glue_catalog_table_serde_library = EXCLUDED.glue_catalog_table_serde_library,
                glue_catalog_table_serde_parameters = EXCLUDED.glue_catalog_table_serde_parameters,
                glue_catalog_table_columns_metadata = EXCLUDED.glue_catalog_table_columns_metadata,
                glue_catalog_table_partition_keys_metadata = EXCLUDED.glue_catalog_table_partition_keys_metadata,
                glue_catalog_table_connection_name = EXCLUDED.glue_catalog_table_connection_name,
                glue_catalog_table_parameters = EXCLUDED.glue_catalog_table_parameters,
                glue_dq_ruleset_description = EXCLUDED.glue_dq_ruleset_description,
                glue_dq_ruleset_dqdl_rules = EXCLUDED.glue_dq_ruleset_dqdl_rules,
                glue_dq_ruleset_created_timestamp = EXCLUDED.glue_dq_ruleset_created_timestamp,
                glue_dq_ruleset_last_modified_timestamp = EXCLUDED.glue_dq_ruleset_last_modified_timestamp,
                updated_time = CURRENT_TIMESTAMP,
                updated_by = 'system'
            WHERE {where_clause};
        """
        
        # Prepare all data tuples
        data_tuples = [_prepare_upsert_data(metadata) for metadata in metadata_list]
        
        # Use execute_batch for efficient batch insertion
        execute_batch(cursor, upsert_query, data_tuples, page_size=batch_size)
        
        logger.info(f"Batch upserted {len(metadata_list)} records into {schema_name}.{target_table}")
        return len(metadata_list)
        
    except Exception as e:
        logger.error(f"Failed to batch upsert {len(metadata_list)} records: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()


def upsert_data(conn, schema_name: str, target_table: str, metadata: Dict[str, Any]) -> None:
    """
    Upsert data into PostgreSQL table (kept for backward compatibility).
    
    Args:
        conn: psycopg2 database connection
        schema_name: Database schema name
        target_table: Target table name
        metadata: Formatted metadata dictionary
    """
    batch_upsert_data(conn, schema_name, target_table, [metadata], batch_size=1)


# ============================================================================
# MAIN SYNC FUNCTION
# ============================================================================

def _process_single_ruleset(glue_client, ruleset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process a single ruleset: fetch metadata, format, and return formatted data.
    Helper function for parallel processing (OPTIMIZATION 3).
    
    Args:
        glue_client: AWS Glue client
        ruleset: Ruleset dictionary
        
    Returns:
        Formatted metadata dictionary or None if processing failed
    """
    try:
        # Extract database and table name from ruleset
        target_table_info = ruleset.get("TargetTable", {})
        database_name = target_table_info.get("DatabaseName")
        table_name = target_table_info.get("TableName")
        
        if not database_name or not table_name:
            logger.debug(f"Ruleset {ruleset.get('Name', 'Unknown')} has no target table info, skipping")
            return None
        
        logger.debug(f"Processing ruleset: {ruleset.get('Name')} for table: {database_name}.{table_name}")
        
        # Fetch related Glue metadata
        table_metadata = fetch_glue_metadata(glue_client, database_name, table_name)
        
        # Format metadata
        formatted = format_metadata(table_metadata, ruleset)
        
        return formatted
        
    except Exception as e:
        logger.warning(f"Error processing ruleset {ruleset.get('Name', 'Unknown')}: {str(e)}")
        return None


def sync_glue_dqdl_ruleset_details(context: Dict[str, Any]) -> Dict[str, int]:
    """
    Delta load for AWS Glue Data Quality ruleset details table.
    Optimized with parallel processing and batch operations.
    
    Flow:
    1. Fetch all rulesets (with parallel detail fetching)
    2. For each ruleset, fetch related Glue metadata (parallel)
    3. Format metadata (parallel)
    4. Batch upsert data
    
    Optimizations applied:
    1. Parallel fetching of ruleset details
    2. Batch database operations
    3. Parallel processing of rulesets
    4. Reduced logging verbosity
    5. Optimized connection usage
    6. Configurable batch sizes
    7. Improved error handling
    """
    conn = context["connection"]
    schema_name = context["schema_name"]
    aws_region = context["aws_region"]
    target_table = "t_glue_dqdl_ruleset_details"
    
    # OPTIMIZATION 6: Configurable batch sizes and workers
    max_workers = int(context.get("max_workers", DEFAULT_MAX_WORKERS))
    batch_size = int(context.get("batch_size", DEFAULT_BATCH_SIZE))
    
    stats = {
        "rulesets_processed": 0,
        "upserts_executed": 0,
        "errors": 0,
        "skipped": 0
    }
    
    error_details = []  # OPTIMIZATION 7: Collect errors for reporting
    
    try:
        logger.info(f"Starting delta load for {target_table} (max_workers={max_workers}, batch_size={batch_size})")
        glue_client = get_glue_client(aws_region)
        
        # 1. Fetch all rulesets (with parallel detail fetching - OPTIMIZATION 1)
        rulesets = fetch_ruleset(glue_client, max_workers=max_workers)
        stats["rulesets_processed"] = len(rulesets)
        
        if not rulesets:
            logger.info("No rulesets found to process")
            return stats
        
        logger.info(f"Processing {len(rulesets)} rulesets in parallel")
        
        # OPTIMIZATION 3: Parallel processing of rulesets
        formatted_metadata_list = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all processing tasks
            future_to_ruleset = {
                executor.submit(_process_single_ruleset, glue_client, ruleset): ruleset
                for ruleset in rulesets
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_ruleset):
                ruleset = future_to_ruleset[future]
                try:
                    result = future.result()
                    if result:
                        formatted_metadata_list.append(result)
                    else:
                        stats["skipped"] += 1
                except Exception as e:
                    ruleset_name = ruleset.get('Name', 'Unknown')
                    error_msg = f"Exception processing ruleset {ruleset_name}: {str(e)}"
                    logger.warning(error_msg)
                    error_details.append(error_msg)
                    stats["errors"] += 1
        
        logger.info(f"Successfully processed {len(formatted_metadata_list)} rulesets "
                   f"(skipped: {stats['skipped']}, errors: {stats['errors']})")
        
        # OPTIMIZATION 2: Batch database operations
        if formatted_metadata_list:
            try:
                # Process in batches to optimize memory and database performance
                total_upserted = 0
                for i in range(0, len(formatted_metadata_list), batch_size):
                    batch = formatted_metadata_list[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(formatted_metadata_list) + batch_size - 1) // batch_size
                    
                    logger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch)} records)")
                    batch_upsert_data(conn, schema_name, target_table, batch, batch_size=batch_size)
                    total_upserted += len(batch)
                
                stats["upserts_executed"] = total_upserted
                logger.info(f"Batch upserted {total_upserted} records in {total_batches} batch(es)")
                
            except Exception as e:
                logger.error(f"Error during batch upsert: {str(e)}")
                error_details.append(f"Batch upsert error: {str(e)}")
                stats["errors"] += len(formatted_metadata_list)
                raise
        
        # Commit all changes (OPTIMIZATION 5: Single commit for all operations)
        conn.commit()
        logger.info("Committed all changes")
        
        # OPTIMIZATION 7: Report errors if any
        if error_details:
            logger.warning(f"Encountered {len(error_details)} errors during processing. "
                          f"First few errors: {error_details[:5]}")
        
        logger.info(f"Delta load completed for {target_table}. Statistics: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error in delta load for {target_table}: {str(e)}")
        conn.rollback()
        # OPTIMIZATION 7: Include error details in exception context
        if error_details:
            logger.error(f"Additional error details: {error_details}")
        raise
