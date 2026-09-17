# Caching notes

A cache sits in front of an expensive or slow operation and serves a
previous result instead of recomputing it. Two things matter most:
invalidation (knowing when a cached value is stale) and key design
(making sure two different requests don't collide on the same key).

Cache-aside is the simplest pattern: check the cache first, and on a miss,
compute the real result and store it before returning.
