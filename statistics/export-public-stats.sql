WITH latest_runs AS (
    SELECT
        EVENT_JSON,
        MIN(EVENT_DATE) OVER () AS FIRST_EVENT_DATE,
        MAX(EVENT_DATE) OVER () AS LAST_EVENT_DATE
    FROM EVENTS
    WHERE EVENT_NAME = 'schody_run'
      AND NULLIF(TRIM(USER_ID), '') IS NOT NULL
      AND NULLIF(TRIM(EVENT_JSON:sc_run_id::STRING), '') IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY UNITY_ENVIRONMENT_NAME, USER_ID, EVENT_JSON:sc_run_id::STRING
        ORDER BY
            TRY_TO_NUMBER(EVENT_JSON:sc_sequence::STRING) DESC NULLS LAST,
            TRY_TO_DOUBLE(EVENT_JSON:sc_active_seconds::STRING) DESC NULLS LAST,
            EVENT_TIMESTAMP DESC NULLS LAST,
            EVENT_ID DESC NULLS LAST
    ) = 1
)
SELECT TO_JSON(OBJECT_CONSTRUCT_KEEP_NULL(
    'schemaVersion', 1,
    'updatedAt', TO_CHAR(
        CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP()),
        'YYYY-MM-DD"T"HH24:MI:SS"Z"'
    ),
    'windowStart', TO_CHAR(MIN(FIRST_EVENT_DATE), 'YYYY-MM-DD'),
    'windowEnd', TO_CHAR(MAX(LAST_EVENT_DATE), 'YYYY-MM-DD'),
    'runs', COUNT(*),
    'deaths', COALESCE(SUM(IFF(EVENT_JSON:sc_report_kind::STRING = 'death', 1, 0)), 0),
    'completedRuns', COALESCE(SUM(IFF(EVENT_JSON:sc_report_kind::STRING = 'completed', 1, 0)), 0)
)) AS PUBLIC_STATS_JSON
FROM latest_runs;
