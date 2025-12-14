Status: Succeeded
Test Event Name: new_one

Response:
{
  "statusCode": 500,
  "status": "error",
  "message": "Sync failed: column reference \"glue_catalog_table_type\" is ambiguous\nLINE 43:             WHERE glue_catalog_table_type IS DISTINCT FROM E...\n                           ^\n"
}

The area below shows the last 4 KB of the execution log.

Function Logs:
n (reached max retries: 4): Rate exceeded
[WARNING]	2025-12-14T18:09:25.252Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Failed to fetch ruleset details for wer432sde: An error occurred (ThrottlingException) when calling the GetDataQualityRuleset operation (reached max retries: 4): Rate exceeded
[WARNING]	2025-12-14T18:09:30.273Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Failed to fetch ruleset details for test: An error occurred (ThrottlingException) when calling the GetDataQualityRuleset operation (reached max retries: 4): Rate exceeded
[WARNING]	2025-12-14T18:09:32.800Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Failed to fetch ruleset details for recommended: An error occurred (ThrottlingException) when calling the GetDataQualityRuleset operation (reached max retries: 4): Rate exceeded
[INFO]	2025-12-14T18:09:32.801Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Fetched 118 rulesets from Glue (out of 159 total)
[INFO]	2025-12-14T18:09:32.801Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Processing 118 rulesets in parallel
[ERROR]	2025-12-14T18:09:32.938Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Failed to fetch metadata for edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2: An error occurred (EntityNotFoundException) when calling the GetTable operation: Entity Not Found
[WARNING]	2025-12-14T18:09:32.938Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Error processing ruleset hcp_terr_2_ruleset: An error occurred (EntityNotFoundException) when calling the GetTable operation: Entity Not Found
[INFO]	2025-12-14T18:09:33.381Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Successfully processed 117 rulesets (skipped: 1, errors: 0)
[ERROR]	2025-12-14T18:09:33.490Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Failed to batch upsert 117 records: column reference "glue_catalog_table_type" is ambiguous
LINE 43:             WHERE glue_catalog_table_type IS DISTINCT FROM E...
                           ^

[ERROR]	2025-12-14T18:09:33.490Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Error during batch upsert: column reference "glue_catalog_table_type" is ambiguous
LINE 43:             WHERE glue_catalog_table_type IS DISTINCT FROM E...
                           ^

[ERROR]	2025-12-14T18:09:33.490Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Error in delta load for t_glue_dqdl_ruleset_details: column reference "glue_catalog_table_type" is ambiguous
LINE 43:             WHERE glue_catalog_table_type IS DISTINCT FROM E...
                           ^

[ERROR]	2025-12-14T18:09:33.492Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Additional error details: ['Batch upsert error: column reference "glue_catalog_table_type" is ambiguous\nLINE 43:             WHERE glue_catalog_table_type IS DISTINCT FROM E...\n                           ^\n']
[ERROR]	2025-12-14T18:09:33.492Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Lambda execution failed: column reference "glue_catalog_table_type" is ambiguous
LINE 43:             WHERE glue_catalog_table_type IS DISTINCT FROM E...
                           ^

Traceback (most recent call last):
  File "/var/task/app.py", line 80, in lambda_handler
    stats = utility.sync_glue_dqdl_ruleset_details(context_params)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/task/utility.py", line 473, in sync_glue_dqdl_ruleset_details
    batch_upsert_data(conn, schema_name, target_table, batch, batch_size=batch_size)
  File "/var/task/utility.py", line 315, in batch_upsert_data
    execute_batch(cursor, upsert_query, data_tuples, page_size=batch_size)
  File "/opt/python/lib/python3.11/site-packages/psycopg2/extras.py", line 1216, in execute_batch
    cur.execute(b";".join(sqls))
psycopg2.errors.AmbiguousColumn: column reference "glue_catalog_table_type" is ambiguous
LINE 43:             WHERE glue_catalog_table_type IS DISTINCT FROM E...
                           ^
[INFO]	2025-12-14T18:09:33.495Z	037cd73d-088e-44ab-aa5d-818f9a81d6a4	Database connection closed
END RequestId: 037cd73d-088e-44ab-aa5d-818f9a81d6a4
REPORT RequestId: 037cd73d-088e-44ab-aa5d-818f9a81d6a4	Duration: 41427.91 ms	Billed Duration: 41839 ms	Memory Size: 3008 MB	Max Memory Used: 117 MB	Init Duration: 411.04 ms

Request ID: 037cd73d-088e-44ab-aa5d-818f9a81d6a4
