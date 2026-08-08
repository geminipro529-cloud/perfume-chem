# Recovery Registers

The bundled registers are search targets, not permission to rewrite missing files.

- `MISSING_EXACT_BYTES_REGISTER.csv` lists required exact artifacts and known hashes where available.
- `VISIBLE_UNMOUNTED_BATCHES_REGISTER.csv` lists research batches visible in screenshots but not yet mounted as exact bytes.
- `FILE_LIBRARY_EXACT_PACKAGE_RECOVERY_QUEUE.csv` lists validated package names and expected hashes from File Library receipts.
- `RESEARCH_REGENERATION_GAP_REGISTER.csv` separates recoverable source-byte gaps from empirical work that never happened.

The collector searches both ordinary files and nested ZIP members. Name matches with hash mismatches remain conflicts. They are never silently accepted as the expected artifact.
