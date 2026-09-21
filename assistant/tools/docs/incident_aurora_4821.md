# Incident INC-4821 -- Aurora billing-sync job

On 2024-11-03, the Aurora billing-sync job began failing with
connection-pool exhaustion errors. Investigation found the pool's
max_idle_time was left at the default 30s, so idle connections were
being recycled faster than the payments service could accept new ones
once traffic picked up -- under sustained load, the pool ran out of
usable connections faster than they could be replaced.

No configuration change is recorded here; see the connection-pooling
library's own documentation for the relevant tuning options.
