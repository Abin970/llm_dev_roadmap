# Aurora authentication

The billing-sync job authenticates to the payments service using a
short-lived token pulled from the `vault-aurora` secret path. Tokens
rotate every 12 hours; the job caches the token in memory and only
re-fetches it on a 401 from the payments service.
