def migrate(cr, version):
    if not version:
        return
    # Preserve one active job per integration identity. Duplicate active jobs
    # are operational duplicates, not business records; cancel extras loudly.
    cr.execute(
        """
        SELECT identity_key, array_agg(id ORDER BY id) AS ids
          FROM queue_job
         WHERE identity_key LIKE 'ecom:%'
           AND state IN ('pending', 'enqueued', 'wait_dependencies')
         GROUP BY identity_key
        HAVING COUNT(*) > 1
        """
    )
    for _key, ids in cr.fetchall():
        cancel_ids = ids[1:]
        cr.execute(
            "UPDATE queue_job SET state = 'cancelled', date_cancelled = NOW() "
            "WHERE id = ANY(%s)",
            (cancel_ids,),
        )
    cr.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS queue_job_ecommerce_identity_active_uniq
            ON queue_job (identity_key)
         WHERE identity_key LIKE 'ecom:%'
           AND state IN ('pending', 'enqueued', 'wait_dependencies')
        """
    )
