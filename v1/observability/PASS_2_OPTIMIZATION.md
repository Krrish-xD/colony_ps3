## Pass 2 Optimization

- **Improvements made**:
  1. Loki config can use `boltdb-shipper` as the object store is set to filesystem. But for a hackathon demo, we want it to be as fast as possible.
  2. The table manager in Loki is not really needed for a 3-minute hackathon. We can remove it entirely to simplify.
  3. Chunk store configs like `max_look_back_period` are zeroed out, which is good. We can also remove `compactor` configs for Loki entirely to avoid background operations taking CPU.
- **What was removed or simplified**:
  - Loki compactor and table manager sections. This avoids heavy IO operations and background compaction.
  - Simplified Loki's schema config down to just index and store, since we don't care about persistence for the demo.
- **Final justification of design**:
  - By removing background compaction and table management from Loki, we free up CPU cycles on the Docker Compose host machine, ensuring that log ingestion is perfectly synchronous and never throttled by internal Loki housekeeping tasks. This directly serves the 15s end-to-end SLA.
