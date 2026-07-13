# M6 Backup And Restore

M6 backup/restore is a local operator workflow. Automated acceptance uses marked temporary data roots only and never touches the user's active `runtime-data`.

## Backup

Stop new submissions, allow active local writes to drain, and run:

```bash
python3 tools/backup_m6_store.py \
  --data-root /absolute/path/to/runtime-data \
  --destination /absolute/path/to/new-backup-directory
```

The destination must be absent or empty. The command checkpoints SQLite through its backup API and copies the content-addressed object store and credential files. `manifest.json` records only relative paths, modes, sizes, and SHA-256 hashes; it never contains credential plaintext.

Keep the returned `inventory_hash`. A GC apply must use the same verified backup manifest and an unchanged inventory hash.

## Verify And Restore

Restore only into an absent or empty directory:

```bash
python3 tools/restore_m6_store.py \
  --manifest /absolute/path/to/backup/manifest.json \
  --destination /absolute/path/to/restored-runtime-data
```

Restore rejects path traversal, missing/unexpected members, hash mismatch, non-empty targets, and credential paths outside the original data root. Credential and journal paths are relocated to the restored root and credential files are forced to mode `0600`.

Start a local verification instance against the restored root with M6 execution disabled:

```bash
AI_DRAMA_DATA_ROOT=/absolute/path/to/restored-runtime-data \
AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=false \
python3 -m uvicorn ai_drama_web.app:create_app --factory --host 127.0.0.1 --port 18000
```

Verify `/api/health`, local supplier credential configured status, projects, chapters, assets, bindings, jobs, and results. Do not print or compare credential plaintext during an operator drill.

## Failure Handling

- `BACKUP_HASH_MISMATCH`: discard the restore target and recopy from a verified backup.
- `RESTORE_DESTINATION_NOT_EMPTY`: choose a new empty destination; never overwrite an existing store.
- `CREDENTIAL_PATH_OUTSIDE_DATA_ROOT`: stop and inspect the source store. Do not rewrite the path manually.
- App startup or semantic comparison failure: keep the original store untouched, leave the production feature flag off, and investigate before cutover.
