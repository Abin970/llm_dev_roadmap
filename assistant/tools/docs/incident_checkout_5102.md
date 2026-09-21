# Incident INC-5102 -- checkout-service

During a flash-sale traffic spike, checkout-service began failing
intermittently. Investigation found the same underlying pattern as an
earlier incident on the Aurora billing-sync job: connection-pool
exhaustion. Idle connections were being recycled well
before the burst of sale traffic arrived, so the pool had too few live
connections on hand when load suddenly jumped.

No configuration change is recorded here; see the connection-pooling
library's own documentation for the relevant tuning options.
