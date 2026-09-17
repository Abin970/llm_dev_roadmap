# Database indexing

An index trades write cost and storage for faster reads on a specific
column or set of columns. Without an index, a lookup filtered on that
column requires scanning every row.

A composite index (multiple columns) only speeds up queries that filter
on a leading prefix of those columns, in order -- an index on (a, b)
helps a query filtering on `a`, or on `a AND b`, but not one filtering on
`b` alone.
