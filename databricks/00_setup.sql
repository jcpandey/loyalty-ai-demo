CREATE CATALOG IF NOT EXISTS loyalty_demo;

CREATE SCHEMA IF NOT EXISTS loyalty_demo.bronze;
CREATE SCHEMA IF NOT EXISTS loyalty_demo.silver;
CREATE SCHEMA IF NOT EXISTS loyalty_demo.gold;
CREATE SCHEMA IF NOT EXISTS loyalty_demo.rag;

CREATE EXTERNAL LOCATION IF NOT EXISTS loyalty_demo_landing_events
URL 's3://loyalty-ai-demo-829742257446-ap-southeast-2/landing/events/'
WITH (STORAGE CREDENTIAL loyalty_demo_s3_cred)
COMMENT 'Synthetic loyalty landing files written by the consumer Lambda';

CREATE EXTERNAL LOCATION IF NOT EXISTS loyalty_demo_bronze_meta
URL 's3://loyalty-ai-demo-829742257446-ap-southeast-2/checkpoints/bronze/'
WITH (STORAGE CREDENTIAL loyalty_demo_s3_cred)
COMMENT 'Auto Loader checkpoint files for Bronze ingestion';

CREATE EXTERNAL LOCATION IF NOT EXISTS loyalty_demo_bronze_schema
URL 's3://loyalty-ai-demo-829742257446-ap-southeast-2/schemas/bronze/'
WITH (STORAGE CREDENTIAL loyalty_demo_s3_cred)
COMMENT 'Auto Loader schema tracking files for Bronze ingestion';

GRANT READ FILES
ON EXTERNAL LOCATION loyalty_demo_landing_events
TO `jc.pandeyj@gmail.com`;

GRANT READ FILES, WRITE FILES
ON EXTERNAL LOCATION loyalty_demo_bronze_meta
TO `jc.pandeyj@gmail.com`;

GRANT READ FILES, WRITE FILES
ON EXTERNAL LOCATION loyalty_demo_bronze_schema
TO `jc.pandeyj@gmail.com`;
