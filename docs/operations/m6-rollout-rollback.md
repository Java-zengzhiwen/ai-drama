# M6 Supplier Execution Rollout And Rollback

This runbook keeps M6 supplier execution disabled by default. Real Provider smoke tests require a separate, explicit authorization and are not part of rollout verification.

## Preconditions

1. Stop new generation submissions and allow active work to drain or record every active provider job ID.
2. Run `python3 tools/inventory_object_store.py --data-root <root>` and retain the dry-run JSON.
3. Create and verify a backup with `python3 tools/backup_m6_store.py --data-root <root> --destination <empty-backup-dir>`.
4. Run `python3 migration/tools/verify_migration.py` and `python3 tools/verify_m6_supplier_model_management.py` with no real Provider credentials in the process environment.
5. Confirm the backup manifest inventory hash matches the current inventory and the credential files are mode `0600`.

## Enable In A Controlled Environment

Set `AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=true` only for the selected local service instance, then restart it. Do not add this setting to the user's production LaunchAgent until a separately approved rollout.

Observe:

- migration and credential recovery status;
- legacy backfill count and preserved provider video IDs;
- submission-attempt states and submit counts;
- `SUPPLIER_RUNTIME_UNAVAILABLE`, credential corruption, and idempotency conflicts;
- queue age, polling status, object persistence, and result availability;
- management API loopback rejection and secret redaction.

Abort immediately if a queued job is submitted twice, an active job loses its provider ID, a credential becomes unreadable, an object hash changes unexpectedly, a management route is reachable remotely, or any real endpoint is contacted without authorization.

## Roll Back

1. Stop the service so no submission or poll transaction is in progress.
2. Set `AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=false` and restart.
3. Verify legacy routes are active, M6 supplier/model/binding/snapshot/job rows remain readable, and no row or object was deleted.
4. Run the inventory command again and compare protected object IDs.
5. Run the migration verifier and the M1-M5 regression verifiers.

Rollback disables new M6 routing. It does not delete M6 audit evidence, immutable versions, credentials, snapshots, jobs, or results.

## Restore From Backup

Restore is an operator action and only targets an absent or empty directory:

```bash
python3 tools/restore_m6_store.py \
  --manifest <backup-dir>/manifest.json \
  --destination <empty-restore-dir>
```

Start a local flag-off instance against the restored directory. Compare project, supplier, model, binding, snapshot, job, result, object, and migration identities before redirecting any service to it. A corrupt manifest, hash mismatch, unexpected member, non-empty destination, or credential path outside the data root is a hard stop.
