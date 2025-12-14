Status: Succeeded
Test Event Name: new_one

Response:
{
  "statusCode": 500,
  "status": "error",
  "message": "Sync failed: column reference \"glue_catalog_table_type\" is ambiguous\nLINE 43:                     WHEN (glue_catalog_table_type IS DISTINC...\n                                   ^\n"
}

The area below shows the last 4 KB of the execution log.

Function Logs:
ists, retrying in 1s (attempt 1/5)
[WARNING]	2025-12-14T18:36:40.498Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Rate limit exceeded for ruleset rule1, retrying in 2s (attempt 2/5)
[WARNING]	2025-12-14T18:36:44.685Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Rate limit exceeded for ruleset global_team_coulumn_exists, retrying in 4s (attempt 3/5)
[WARNING]	2025-12-14T18:36:45.527Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Rate limit exceeded for ruleset wer432sde, retrying in 2s (attempt 2/5)
[INFO]	2025-12-14T18:36:48.863Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Fetched 159 rulesets from Glue (out of 159 total, 0 failed)
[INFO]	2025-12-14T18:36:48.864Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Processing 159 rulesets in parallel
[WARNING]	2025-12-14T18:36:49.124Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[WARNING]	2025-12-14T18:36:49.125Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Error processing ruleset hcp_terr_2_ruleset: Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[WARNING]	2025-12-14T18:36:50.158Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[WARNING]	2025-12-14T18:36:50.158Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Error processing ruleset edb-iris-verso-dt-hcp-terr-2-ruleset: Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[INFO]	2025-12-14T18:36:50.358Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Successfully processed 157 rulesets (skipped: 2, errors: 0)
[ERROR]	2025-12-14T18:36:50.427Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Failed to batch upsert 157 records: column reference "glue_catalog_table_type" is ambiguous
LINE 43:                     WHEN (glue_catalog_table_type IS DISTINC...
                                   ^

[ERROR]	2025-12-14T18:36:50.427Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Error during batch upsert: column reference "glue_catalog_table_type" is ambiguous
LINE 43:                     WHEN (glue_catalog_table_type IS DISTINC...
                                   ^

[ERROR]	2025-12-14T18:36:50.427Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Error in delta load for t_glue_dqdl_ruleset_details: column reference "glue_catalog_table_type" is ambiguous
LINE 43:                     WHEN (glue_catalog_table_type IS DISTINC...
                                   ^

[ERROR]	2025-12-14T18:36:50.428Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Additional error details: ['Batch upsert error: column reference "glue_catalog_table_type" is ambiguous\nLINE 43:                     WHEN (glue_catalog_table_type IS DISTINC...\n                                   ^\n']
[ERROR]	2025-12-14T18:36:50.428Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Lambda execution failed: column reference "glue_catalog_table_type" is ambiguous
LINE 43:                     WHEN (glue_catalog_table_type IS DISTINC...
                                   ^

Traceback (most recent call last):
  File "/var/task/app.py", line 80, in lambda_handler
    stats = utility.sync_glue_dqdl_ruleset_details(context_params)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/task/utility.py", line 559, in sync_glue_dqdl_ruleset_details
    batch_upsert_data(conn, schema_name, target_table, batch, batch_size=batch_size)
  File "/var/task/utility.py", line 401, in batch_upsert_data
    execute_batch(cursor, upsert_query, data_tuples, page_size=batch_size)
  File "/opt/python/lib/python3.11/site-packages/psycopg2/extras.py", line 1216, in execute_batch
    cur.execute(b";".join(sqls))
psycopg2.errors.AmbiguousColumn: column reference "glue_catalog_table_type" is ambiguous
LINE 43:                     WHEN (glue_catalog_table_type IS DISTINC...
                                   ^
[INFO]	2025-12-14T18:36:50.432Z	5523a8f3-baaa-4472-8fe9-85279a65d9c9	Database connection closed
END RequestId: 5523a8f3-baaa-4472-8fe9-85279a65d9c9
REPORT RequestId: 5523a8f3-baaa-4472-8fe9-85279a65d9c9	Duration: 136829.69 ms	Billed Duration: 137279 ms	Memory Size: 3008 MB	Max Memory Used: 117 MB	Init Duration: 448.93 ms

Request ID: 5523a8f3-baaa-4472-8fe9-85279a65d9c9
