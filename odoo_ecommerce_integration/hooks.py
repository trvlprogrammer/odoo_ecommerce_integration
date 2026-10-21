def ensure_partial_indexes(cr):
    cr.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS queue_job_ecommerce_identity_active_uniq
            ON queue_job (identity_key)
         WHERE identity_key LIKE 'ecom:%'
           AND state IN ('pending', 'enqueued', 'wait_dependencies')
        """
    )


def post_init_hook(env):
    ensure_partial_indexes(env.cr)
