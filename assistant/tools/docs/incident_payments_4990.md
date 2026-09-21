# Incident INC-4990 -- payments-service

payments-service began seeing cascading 429 (rate limited) errors from
a third-party payment provider. Investigation found that a burst of
failed calls triggered retries with no cap and no delay between
attempts, so the retry traffic itself pushed the account further past
the provider's rate limit, prolonging the outage.

No configuration change is recorded here; see the retry/backoff
library's own documentation for the relevant tuning options.
