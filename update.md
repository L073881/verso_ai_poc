Status: Succeeded
Test Event Name: new_one

Response:
{
  "statusCode": 200,
  "status": "success",
  "message": "Successfully synced data into t_glue_dqdl_ruleset_details",
  "target_table": "t_glue_dqdl_ruleset_details",
  "statistics": {
    "rulesets_processed": 0,
    "upserts_executed": 0,
    "errors": 0
  }
}

The area below shows the last 4 KB of the execution log.

Function Logs:
START RequestId: dede7240-7773-4a50-b509-a5882e39e056 Version: $LATEST
[INFO]	2025-12-14T17:43:49.551Z	dede7240-7773-4a50-b509-a5882e39e056	Starting Glue DQDL Ruleset Sync
[INFO]	2025-12-14T17:43:49.551Z	dede7240-7773-4a50-b509-a5882e39e056	Fetching database credentials from Secrets Manager
[INFO]	2025-12-14T17:43:49.565Z	dede7240-7773-4a50-b509-a5882e39e056	Found credentials in environment variables.
[INFO]	2025-12-14T17:43:49.773Z	dede7240-7773-4a50-b509-a5882e39e056	Database credentials retrieved successfully
[INFO]	2025-12-14T17:43:49.774Z	dede7240-7773-4a50-b509-a5882e39e056	Connecting to Aurora database
[INFO]	2025-12-14T17:43:49.802Z	dede7240-7773-4a50-b509-a5882e39e056	Database connection established successfully
[INFO]	2025-12-14T17:43:49.802Z	dede7240-7773-4a50-b509-a5882e39e056	Starting delta load for t_glue_dqdl_ruleset_details
[INFO]	2025-12-14T17:43:49.865Z	dede7240-7773-4a50-b509-a5882e39e056	Fetching all rulesets from Glue
[ERROR]	2025-12-14T17:43:49.882Z	dede7240-7773-4a50-b509-a5882e39e056	Failed to fetch rulesets: Operation cannot be paginated: list_data_quality_rulesets
[INFO]	2025-12-14T17:43:49.882Z	dede7240-7773-4a50-b509-a5882e39e056	Processing 0 rulesets
[INFO]	2025-12-14T17:43:49.882Z	dede7240-7773-4a50-b509-a5882e39e056	Committed all changes
[INFO]	2025-12-14T17:43:49.882Z	dede7240-7773-4a50-b509-a5882e39e056	Delta load completed for t_glue_dqdl_ruleset_details. Statistics: {'rulesets_processed': 0, 'upserts_executed': 0, 'errors': 0}
[INFO]	2025-12-14T17:43:49.882Z	dede7240-7773-4a50-b509-a5882e39e056	Sync completed successfully for t_glue_dqdl_ruleset_details
[INFO]	2025-12-14T17:43:49.882Z	dede7240-7773-4a50-b509-a5882e39e056	Database connection closed
END RequestId: dede7240-7773-4a50-b509-a5882e39e056
REPORT RequestId: dede7240-7773-4a50-b509-a5882e39e056	Duration: 332.92 ms	Billed Duration: 780 ms	Memory Size: 3008 MB	Max Memory Used: 101 MB	Init Duration: 446.20 ms
