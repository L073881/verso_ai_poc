Status: Succeeded
Test Event Name: new_one

Response:
{
  "statusCode": 200,
  "status": "success",
  "message": "Successfully synced data into t_glue_dqdl_ruleset_details",
  "target_table": "t_glue_dqdl_ruleset_details",
  "statistics": {
    "rulesets_processed": 158,
    "upserts_executed": 156,
    "errors": 2
  }
}

The area below shows the last 4 KB of the execution log.

Function Logs:
ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetched metadata for table: edb_dq_test_database2.edb_aurora_emdm_dev_edb_axon_md_b_md_glossary
[INFO]	2025-12-14T18:49:27.997Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Processing ruleset: glossary test for table: axon_dev.edb_aurora_emdm_dev_edb_axon_md_b_md_glossary
[INFO]	2025-12-14T18:49:27.997Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetching metadata for table: axon_dev.edb_aurora_emdm_dev_edb_axon_md_b_md_glossary
[INFO]	2025-12-14T18:49:28.029Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetched metadata for table: axon_dev.edb_aurora_emdm_dev_edb_axon_md_b_md_glossary
[INFO]	2025-12-14T18:49:28.031Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Processing ruleset: Axon_dataset_ruleset for table: axon_dev.edb_aurora_emdm_dev_edb_axon_md_b_md_dataset
[INFO]	2025-12-14T18:49:28.031Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetching metadata for table: axon_dev.edb_aurora_emdm_dev_edb_axon_md_b_md_dataset
[INFO]	2025-12-14T18:49:28.071Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetched metadata for table: axon_dev.edb_aurora_emdm_dev_edb_axon_md_b_md_dataset
[INFO]	2025-12-14T18:49:28.073Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Processing ruleset: demo_ruleset for table: edb_glue_datacatalog_usecase.edb_audit_edb_dev_abc_t_dq_error_log
[INFO]	2025-12-14T18:49:28.073Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetching metadata for table: edb_glue_datacatalog_usecase.edb_audit_edb_dev_abc_t_dq_error_log
[INFO]	2025-12-14T18:49:28.115Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetched metadata for table: edb_glue_datacatalog_usecase.edb_audit_edb_dev_abc_t_dq_error_log
[INFO]	2025-12-14T18:49:28.118Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Processing ruleset: recommended_ruleset for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.118Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetching metadata for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.144Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetched metadata for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.146Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Processing ruleset: recommended for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.146Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetching metadata for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.185Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetched metadata for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.187Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Processing ruleset: test for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.187Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetching metadata for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.235Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Fetched metadata for table: edb_poc_glue_usecase.edb_poc_glue_usecase_edb_audit_edb_dev_abc_t_dq_error_log_unpartitioned
[INFO]	2025-12-14T18:49:28.240Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Committed all changes
[INFO]	2025-12-14T18:49:28.240Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Delta load completed for t_glue_dqdl_ruleset_details. Statistics: {'rulesets_processed': 158, 'upserts_executed': 156, 'errors': 2}
[INFO]	2025-12-14T18:49:28.240Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Sync completed successfully for t_glue_dqdl_ruleset_details
[INFO]	2025-12-14T18:49:28.240Z	ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Database connection closed
END RequestId: ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec
REPORT RequestId: ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec	Duration: 140259.10 ms	Billed Duration: 140678 ms	Memory Size: 3008 MB	Max Memory Used: 102 MB	Init Duration: 418.29 ms

Request ID: ba9e5955-4351-4ed4-b2f2-1d0f50dbb6ec
