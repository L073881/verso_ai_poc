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
from psycopg2.extras import Json
from typing import Any, Dict, List, Optional
import logging
import json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def fetch_ruleset(glue_client) -> List[Dict[str, Any]]:
    """
    Fetch all Data Quality rulesets from AWS Glue.
    
    Args:
        glue_client: AWS Glue client
        
    Returns:
        List of ruleset dictionaries with full details
    """
    try:
        logger.info("Fetching all rulesets from Glue")
        rulesets = []
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
            
            # Process rulesets from this page
            for ruleset in response.get("Rulesets", []):
                # Fetch full ruleset details
                try:
                    ruleset_detail = glue_client.get_data_quality_ruleset(
                        Name=ruleset["Name"]
                    )
                    rulesets.append(ruleset_detail)
                except Exception as e:
                    logger.warning(f"Failed to fetch ruleset details for {ruleset['Name']}: {str(e)}")
                    continue
            
            # Check if there are more results
            next_token = response.get("NextToken")
            if not next_token:
                break
        
        logger.info(f"Fetched {len(rulesets)} rulesets from Glue")
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
        logger.info(f"Fetching metadata for table: {database_name}.{table_name}")
        response = glue_client.get_table(DatabaseName=database_name, Name=table_name)
        table = response.get("Table", {})
        logger.info(f"Fetched metadata for table: {database_name}.{table_name}")
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


def upsert_data(conn, schema_name: str, target_table: str, metadata: Dict[str, Any]) -> None:
    """
    Upsert data into PostgreSQL table.
    Only updates when data has actually changed.
    
    Uses a two-step approach:
    1. Check if record exists and if data has changed
    2. Only update if data has changed
    
    Args:
        conn: psycopg2 database connection
        schema_name: Database schema name
        target_table: Target table name
        metadata: Formatted metadata dictionary
    """
    cursor = None
    try:
        cursor = conn.cursor()
        
        # First, check if record exists and compare data
        check_query = f"""
            SELECT 
                glue_catalog_table_type,
                glue_catalog_table_storage_location,
                glue_catalog_table_input_format,
                glue_catalog_table_output_format,
                glue_catalog_table_serde_library,
                glue_catalog_table_serde_parameters::jsonb,
                glue_catalog_table_columns_metadata::jsonb,
                glue_catalog_table_partition_keys_metadata::jsonb,
                glue_catalog_table_connection_name,
                glue_catalog_table_parameters::jsonb,
                glue_dq_ruleset_description,
                glue_dq_ruleset_dqdl_rules,
                glue_dq_ruleset_created_timestamp,
                glue_dq_ruleset_last_modified_timestamp
            FROM {schema_name}.{target_table}
            WHERE glue_catalog_database_name = %s
              AND glue_catalog_table_name = %s
              AND glue_dq_ruleset_name = %s;
        """
        
        cursor.execute(check_query, (
            metadata["database_name"],
            metadata["table_name"],
            metadata["ruleset_name"]
        ))
        
        existing_row = cursor.fetchone()
        
        # Prepare new values for comparison (use raw values, not Json wrappers)
        new_values = {
            "glue_catalog_table_type": metadata["table_type"],
            "glue_catalog_table_storage_location": metadata["storage_location"],
            "glue_catalog_table_input_format": metadata["input_format"],
            "glue_catalog_table_output_format": metadata["output_format"],
            "glue_catalog_table_serde_library": metadata["serde_library"],
            "glue_catalog_table_serde_parameters": metadata["serde_parameters"],
            "glue_catalog_table_columns_metadata": metadata["columns_metadata"],
            "glue_catalog_table_partition_keys_metadata": metadata["partition_keys_metadata"],
            "glue_catalog_table_connection_name": metadata["connection_name"],
            "glue_catalog_table_parameters": metadata["parameters"],
            "glue_dq_ruleset_description": metadata["ruleset_description"],
            "glue_dq_ruleset_dqdl_rules": metadata["ruleset_dqdl"],
            "glue_dq_ruleset_created_timestamp": metadata["ruleset_created"],
            "glue_dq_ruleset_last_modified_timestamp": metadata["ruleset_modified"]
        }
        
        # Check if data has changed
        data_changed = True
        if existing_row:
            # Compare each field
            existing_values = {
                "glue_catalog_table_type": existing_row[0],
                "glue_catalog_table_storage_location": existing_row[1],
                "glue_catalog_table_input_format": existing_row[2],
                "glue_catalog_table_output_format": existing_row[3],
                "glue_catalog_table_serde_library": existing_row[4],
                "glue_catalog_table_serde_parameters": existing_row[5] if existing_row[5] else {},
                "glue_catalog_table_columns_metadata": existing_row[6] if existing_row[6] else [],
                "glue_catalog_table_partition_keys_metadata": existing_row[7] if existing_row[7] else [],
                "glue_catalog_table_connection_name": existing_row[8],
                "glue_catalog_table_parameters": existing_row[9] if existing_row[9] else {},
                "glue_dq_ruleset_description": existing_row[10],
                "glue_dq_ruleset_dqdl_rules": existing_row[11],
                "glue_dq_ruleset_created_timestamp": existing_row[12],
                "glue_dq_ruleset_last_modified_timestamp": existing_row[13]
            }
            
            # Compare values (handle JSON comparison properly)
            data_changed = False
            for key in new_values:
                old_val = existing_values.get(key)
                new_val = new_values.get(key)
                
                # Handle JSON/dict/list comparison
                if key in ["glue_catalog_table_serde_parameters", "glue_catalog_table_columns_metadata", 
                          "glue_catalog_table_partition_keys_metadata", "glue_catalog_table_parameters"]:
                    # Normalize JSON values for comparison
                    old_normalized = json.dumps(old_val, sort_keys=True, default=str) if old_val else "{}"
                    new_normalized = json.dumps(new_val, sort_keys=True, default=str) if new_val else "{}"
                    if old_normalized != new_normalized:
                        data_changed = True
                        break
                else:
                    # Regular comparison (handle None values)
                    if old_val != new_val:
                        # Check if both are None or empty
                        if (old_val is None or old_val == '') and (new_val is None or new_val == ''):
                            continue
                        data_changed = True
                        break
        
        # Only insert/update if record doesn't exist or data has changed
        if not existing_row or data_changed:
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
                    updated_by = 'system';
            """
            
            cursor.execute(upsert_query, (
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
            ))
            
            if existing_row and data_changed:
                logger.debug(f"Updated metadata for {metadata['database_name']}.{metadata['table_name']} (ruleset: {metadata['ruleset_name'] or 'N/A'}) - data changed")
            elif not existing_row:
                logger.debug(f"Inserted metadata for {metadata['database_name']}.{metadata['table_name']} (ruleset: {metadata['ruleset_name'] or 'N/A'})")
        else:
            logger.debug(f"Skipped update for {metadata['database_name']}.{metadata['table_name']} (ruleset: {metadata['ruleset_name'] or 'N/A'}) - no changes detected")
        
    except Exception as e:
        logger.error(f"Failed to upsert metadata for {metadata['database_name']}.{metadata['table_name']}: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()


# ============================================================================
# MAIN SYNC FUNCTION
# ============================================================================

def sync_glue_dqdl_ruleset_details(context: Dict[str, Any]) -> Dict[str, int]:
    """
    Delta load for AWS Glue Data Quality ruleset details table.
    
    Flow:
    1. Fetch all rulesets
    2. For each ruleset, fetch related Glue metadata
    3. Format metadata
    4. Upsert data
    """
    conn = context["connection"]
    schema_name = context["schema_name"]
    aws_region = context["aws_region"]
    target_table = "t_glue_dqdl_ruleset_details"
    
    stats = {
        "rulesets_processed": 0,
        "upserts_executed": 0,
        "errors": 0
    }
    
    try:
        logger.info(f"Starting delta load for {target_table}")
        glue_client = get_glue_client(aws_region)
        
        # 1. Fetch all rulesets
        rulesets = fetch_ruleset(glue_client)
        stats["rulesets_processed"] = len(rulesets)
        
        logger.info(f"Processing {len(rulesets)} rulesets")
        
        # Process each ruleset
        for ruleset in rulesets:
            try:
                # Extract database and table name from ruleset
                target_table_info = ruleset.get("TargetTable", {})
                database_name = target_table_info.get("DatabaseName")
                table_name = target_table_info.get("TableName")
                
                if not database_name or not table_name:
                    logger.warning(f"Ruleset {ruleset.get('Name', 'Unknown')} has no target table info, skipping")
                    stats["errors"] += 1
                    continue
                
                logger.info(f"Processing ruleset: {ruleset.get('Name')} for table: {database_name}.{table_name}")
                
                # 2. Fetch related Glue metadata
                table_metadata = fetch_glue_metadata(glue_client, database_name, table_name)
                
                # 3. Format metadata
                formatted = format_metadata(table_metadata, ruleset)
                
                # 4. Upsert data
                upsert_data(conn, schema_name, target_table, formatted)
                stats["upserts_executed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing ruleset {ruleset.get('Name', 'Unknown')}: {str(e)}")
                stats["errors"] += 1
                continue
        
        # Commit all changes
        conn.commit()
        logger.info("Committed all changes")
        
        logger.info(f"Delta load completed for {target_table}. Statistics: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error in delta load for {target_table}: {str(e)}")
        conn.rollback()
        raise
