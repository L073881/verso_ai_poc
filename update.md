Status: Succeeded
Test Event Name: new_one

Response:
{
  "statusCode": 200,
  "status": "success",
  "message": "Successfully synced data into t_glue_dqdl_ruleset_details",
  "target_table": "t_glue_dqdl_ruleset_details",
  "statistics": {
    "rulesets_processed": 85,
    "upserts_executed": 83,
    "errors": 0,
    "skipped": 2
  }
}

The area below shows the last 4 KB of the execution log.

Function Logs:
bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset segment_rule, skipping
[WARNING]	2025-12-14T18:20:55.556Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset tes_rule, skipping
[WARNING]	2025-12-14T18:20:55.695Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset hcp_segmenation_ruleset, skipping
[WARNING]	2025-12-14T18:20:56.008Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset edb-iris-dd-rft-specialty-pharmacy-ruleset, skipping
[WARNING]	2025-12-14T18:20:56.924Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset Rule1, skipping
[WARNING]	2025-12-14T18:20:57.507Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset test_rule, skipping
[WARNING]	2025-12-14T18:20:57.669Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset alignment-1.0-ruleset, skipping
[WARNING]	2025-12-14T18:20:57.978Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset ref_test, skipping
[WARNING]	2025-12-14T18:21:00.219Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset test_o5, skipping
[WARNING]	2025-12-14T18:21:02.813Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset edb-iris-cost-file-data-quality-ruleset, skipping
[WARNING]	2025-12-14T18:21:02.824Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset test2, skipping
[WARNING]	2025-12-14T18:21:06.284Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset wer432sde, skipping
[WARNING]	2025-12-14T18:21:06.394Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset test_null_rule, skipping
[WARNING]	2025-12-14T18:21:08.781Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset glossary test, skipping
[WARNING]	2025-12-14T18:21:10.511Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset test_rules, skipping
[WARNING]	2025-12-14T18:21:11.939Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Rate limit exceeded for ruleset recommended, skipping
[INFO]	2025-12-14T18:21:11.940Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Fetched 85 rulesets from Glue (out of 159 total)
[INFO]	2025-12-14T18:21:11.940Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Processing 85 rulesets in parallel
[WARNING]	2025-12-14T18:21:12.140Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[WARNING]	2025-12-14T18:21:12.143Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Error processing ruleset hcp_terr_2_ruleset: Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[WARNING]	2025-12-14T18:21:12.387Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[WARNING]	2025-12-14T18:21:12.388Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Error processing ruleset edb-iris-verso-dt-hcp-terr-2-ruleset: Table edb_iris_lilly_zaidyn_data_feeds.hcp-terr-2 not found in Glue catalog
[INFO]	2025-12-14T18:21:12.482Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Successfully processed 83 rulesets (skipped: 2, errors: 0)
[INFO]	2025-12-14T18:21:13.394Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Batch upserted 83 records into edb_dev_dpo.t_glue_dqdl_ruleset_details
[INFO]	2025-12-14T18:21:13.394Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Batch upserted 83 records in 1 batch(es)
[INFO]	2025-12-14T18:21:13.398Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Committed all changes
[INFO]	2025-12-14T18:21:13.399Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Delta load completed for t_glue_dqdl_ruleset_details. Statistics: {'rulesets_processed': 85, 'upserts_executed': 83, 'errors': 0, 'skipped': 2}
[INFO]	2025-12-14T18:21:13.399Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Sync completed successfully for t_glue_dqdl_ruleset_details
[INFO]	2025-12-14T18:21:13.400Z	bf00768f-2df7-4ff8-bae6-45f647b78288	Database connection closed
END RequestId: bf00768f-2df7-4ff8-bae6-45f647b78288
REPORT RequestId: bf00768f-2df7-4ff8-bae6-45f647b78288	Duration: 74839.91 ms	Billed Duration: 75331 ms	Memory Size: 3008 MB	Max Memory Used: 115 MB	Init Duration: 490.43 ms

Request ID: bf00768f-2df7-4ff8-bae6-45f647b78288
