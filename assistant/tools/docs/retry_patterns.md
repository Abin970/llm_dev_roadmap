# Retry patterns

Fixed-delay retries can cause a thundering herd: every caller retries at
the same instant and collides again. Exponential backoff with jitter
spreads retries out over time instead.

Never retry an operation with a side effect (sending an email, charging a
card, writing a row) unless it's idempotent -- an ambiguous failure
followed by a blind retry can duplicate the action.
