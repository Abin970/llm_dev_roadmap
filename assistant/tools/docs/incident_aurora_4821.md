# Incident INC-4821 -- Aurora billing-sync job

On 2024-11-03, the Aurora billing-sync job began failing with
connection-pool exhaustion errors. Root cause: the pool's max_idle_time
was left at the default 30s, so connections were being recycled faster
than the payments service could accept new ones under load.

Fix: max_idle_time was raised from 30s to 90s. A hard cap of 7 retries
before a message is dead-lettered to the `aurora-dlq` queue was also
added -- there was previously no cap, which is part of why the incident
cascaded as long as it did.
