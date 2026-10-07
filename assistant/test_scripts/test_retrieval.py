import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "week5_rag_fundamentals" / "experiments"))

from retrieval import retrieve, format_hits
from vectorstore import Chunk, Hit
from golden_retrieval import GOLDEN

# ---------------------------------------------------------------------------
# Part 1 -- format_hits, OFFLINE (made-up hits, no API call, no cost)
# ---------------------------------------------------------------------------
def fake_hit(i, section=""):
    return Hit(chunk=Chunk(chunk_id=f"postgres:page#{i}", doc_id="postgres:page", text=f"body {i}",
                           source="postgres", doc_type="vendor_doc", layer="database",
                           url="https://example.com/page", title="PostgreSQL 18", section=section),
               score=0.9)

assert format_hits([]) == "(no relevant results)", repr(format_hits([]))

out = format_hits([fake_hit(0, "19.3 › 19.3.1 Settings"), fake_hit(1)])
blocks = out.split("\n\n")
assert len(blocks) == 2, "blocks must be separated by exactly one blank line"
assert blocks[0].startswith("[postgres:page#0] PostgreSQL 18 › 19.3 › 19.3.1 Settings (https://example.com/page)\n"), blocks[0]
assert blocks[1].startswith("[postgres:page#1] PostgreSQL 18 (https://example.com/page)\n"), blocks[1]   # no dangling separator
assert blocks[0].endswith("body 0")
assert "0.9" not in out, "scores must not appear in the evidence text"
print("ok: format_hits -- empty text, header line, section handling, blank-line separation, no score")

# ---------------------------------------------------------------------------
# Part 2 -- LIVE: real questions against the Phase A index.
# Each retrieve() embeds ONE short question (~20 tokens): a tiny fraction of a cent.
# ---------------------------------------------------------------------------
norm = lambda s: " ".join(s.lower().split())
by_id = {q.qid: q for q in GOLDEN}
VENDOR, ONCALL = ("vendor_doc",), ("runbook", "postmortem")

print("\ntop-3 for four Phase A golden questions (vendor docs for db/orch-04, runbooks for orch-01/05):")
for qid, doc_types in [("db-01", VENDOR), ("orch-04", VENDOR), ("orch-01", ONCALL), ("orch-05", ONCALL)]:
    q = by_id[qid]
    hits = retrieve(q.question, k=3, doc_types=doc_types)
    assert 0 < len(hits) <= 3
    assert all(h.chunk.doc_type in doc_types for h in hits), f"{qid}: doc_type filter was ignored"
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    found = any(h.chunk.doc_id == e.doc_id and any(norm(m) in norm(h.chunk.text) for m in e.markers)
                for h in hits for e in q.expected)
    print(f"\n[{qid}] {q.question[:80]}...   answering passage in top 3: {found}")
    for h in hits:
        print(f"   {h.score:.3f}  {h.chunk.chunk_id[:70]}   § {h.chunk.section[:40]}")

# ---------------------------------------------------------------------------
# The two filters
# ---------------------------------------------------------------------------
db_only = retrieve("how long are idle connections kept open?", k=5, doc_types=VENDOR, layer="database")
assert db_only and all(h.chunk.layer == "database" for h in db_only), "layer filter was ignored"
print(f"\nok: layer='database' filter respected ({len(db_only)} hits, all database)")

wrong = retrieve(by_id["db-01"].question, k=3, doc_types=("postmortem",))
print(f"ok: asking for postmortems on a Phase A index returns {len(wrong)} hits (none are loaded yet)")

# ---------------------------------------------------------------------------
# A question that is NOT in the corpus: top-k always returns k chunks anyway
# ---------------------------------------------------------------------------
na = retrieve(by_id["na-04"].question, k=3, doc_types=VENDOR)
real = retrieve(by_id["db-01"].question, k=1, doc_types=VENDOR)
print(f"\nnot-in-corpus question (na-04, Kong): top scores {[round(h.score, 3) for h in na]}  <- it still returns {len(na)} chunks")
print(f"real question (db-01):               top score  {round(real[0].score, 3)}")

print("\nall retrieval checks passed")



# ok: format_hits -- empty text, header line, section handling, blank-line separation, no score

# top-3 for four Phase A golden questions (vendor docs for db/orch-04, runbooks for orch-01/05):

# [db-01] What does idle_in_transaction_session_timeout do in PostgreSQL, and what's its d...   answering passage in top 3: True
#    0.706  postgres:runtime-config-client#7   § 
#    0.609  postgres:runtime-config-client#6   § 
#    0.590  postgres:monitoring-stats#59   § 

{"chunk_id": "postgres:runtime-config-client#6", "doc_id": "postgres:runtime-config-client", "text": "PostgreSQL treats the settings `origin` and `local` the same internally. Third-party replication systems may use these two values for their internal purposes, for example using `local` to designate a session whose changes should not be replicated.\n\n    Since foreign keys are implemented as triggers, setting this parameter to `replica` also disables all foreign key checks, which can leave data in an inconsistent state if improperly used.\n\n`statement_timeout` (`integer`)\n:   Abort any statement that takes more than the specified amount of time. If `log_min_error_statement` is set to `ERROR` or lower, the statement that timed out will also be logged. If this value is specified without units, it is taken as milliseconds. A value of zero (the default) disables the timeout.\n\n    The timeout is measured from the time a command arrives at the server until it is completed by the server. If multiple SQL statements appear in a single simple-query message, the timeout is applied to each statement separately. (PostgreSQL versions before 13 usually treated the timeout as applying to the whole query string.) In extended query protocol, the timeout starts running when any query-related message (Parse, Bind, Execute, Describe) arrives, and it is canceled by completion of an Execute or Sync message.\n\n    Setting `statement_timeout` in `postgresql.conf` is not recommended because it would affect all sessions.\n\n`transaction_timeout` (`integer`)\n:   Terminate any session that spans longer than the specified amount of time in a transaction. The limit applies both to explicit transactions (started with `BEGIN`) and to an implicitly started transaction corresponding to a single statement. If this value is specified without units, it is taken as milliseconds. A value of zero (the default) disables the timeout.\n\n    If `transaction_timeout` is shorter or equal to `idle_in_transaction_session_timeout` or `statement_timeout` then the longer timeout is ignored.\n\n    Setting `transaction_timeout` in `postgresql.conf` is not recommended because it would affect all sessions.\n\n    ### Note\n\n    Prepared transactions are not subject to this timeout.", "source": "postgres", "doc_type": "vendor_doc", "layer": "database", "url": "https://www.postgresql.org/docs/18/runtime-config-client.html", "title": "19.11. Client Connection Defaults", "section": ""}
{"chunk_id": "postgres:runtime-config-client#7", "doc_id": "postgres:runtime-config-client", "text": "Setting `transaction_timeout` in `postgresql.conf` is not recommended because it would affect all sessions.\n\n    ### Note\n\n    Prepared transactions are not subject to this timeout.\n\n`lock_timeout` (`integer`)\n:   Abort any statement that waits longer than the specified amount of time while attempting to acquire a lock on a table, index, row, or other database object. The time limit applies separately to each lock acquisition attempt. The limit applies both to explicit locking requests (such as `LOCK TABLE`, or `SELECT FOR UPDATE` without `NOWAIT`) and to implicitly-acquired locks. If this value is specified without units, it is taken as milliseconds. A value of zero (the default) disables the timeout.\n\n    Unlike `statement_timeout`, this timeout can only occur while waiting for locks. Note that if `statement_timeout` is nonzero, it is rather pointless to set `lock_timeout` to the same or larger value, since the statement timeout would always trigger first. If `log_min_error_statement` is set to `ERROR` or lower, the statement that timed out will be logged.\n\n    Setting `lock_timeout` in `postgresql.conf` is not recommended because it would affect all sessions.\n\n`idle_in_transaction_session_timeout` (`integer`)\n:   Terminate any session that has been idle (that is, waiting for a client query) within an open transaction for longer than the specified amount of time. If this value is specified without units, it is taken as milliseconds. A value of zero (the default) disables the timeout.\n\n    This option can be used to ensure that idle sessions do not hold locks for an unreasonable amount of time. Even when no significant locks are held, an open transaction prevents vacuuming away recently-dead tuples that may be visible only to this transaction; so remaining idle for a long time can contribute to table bloat. See [Section\u00a024.1](routine-vacuuming.html \"24.1.\u00a0Routine Vacuuming\") for more details.\n\n`idle_session_timeout` (`integer`)\n:   Terminate any session that has been idle (that is, waiting for a client query), but not within an open transaction, for longer than the specified amount of time. If this value is specified without units, it is taken as milliseconds. A value of zero (the default) disables the timeout.", "source": "postgres", "doc_type": "vendor_doc", "layer": "database", "url": "https://www.postgresql.org/docs/18/runtime-config-client.html", "title": "19.11. Client Connection Defaults", "section": ""}


# [orch-04] What's the difference between a failing liveness probe and a failing readiness p...   answering passage in top 3: True
#    0.754  kubernetes:content/en/docs/tasks/configure-pod-container/configure-liv   § 
#    0.681  kubernetes:content/en/docs/concepts/workloads/pods/probes.md#1   § 
#    0.679  kubernetes:content/en/docs/concepts/workloads/pods/probes.md#2   § 

{"chunk_id": "kubernetes:content/en/docs/concepts/workloads/pods/probes.md#1", "doc_id": "kubernetes:content/en/docs/concepts/workloads/pods/probes.md", "text": "Liveness probes can be a powerful way to recover from application failures,\nbut they should be used with caution.\nLiveness probes must be configured carefully to ensure that they truly indicate\nunrecoverable application failure, for example a deadlock.\n\nIncorrect implementation of liveness probes can lead to cascading failures.\nThis results in restarting of container under high load; failed client requests\nas your application became less scalable; and increased workload on remaining\npods due to some failed pods. Understand the difference between liveness and\nreadiness probes and when to apply them for your app.\n\n### Readiness probe {#readiness-probe}\n\nReadiness probes determine when a container is ready to accept traffic.\nThis is useful when waiting for an application to perform time-consuming initial\ntasks, such as establishing network connections, loading files, and warming\ncaches.\nReadiness probes can also be useful later in the container\u2019s lifecycle,\nfor example, when recovering from temporary faults or overloads.\n\nIf the readiness probe returns a failed state, the\nEndpointSlice\ncontroller removes the Pod's IP address from the EndpointSlices of all Services\nthat match the Pod.\n\nReadiness probes run on the container during its whole lifecycle.\n\nIf you want to be able to drain requests when the Pod is deleted, you do not\nnecessarily need a readiness probe; when the Pod is deleted, the corresponding\nendpoint in the EndpointSlice will update its [conditions](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/#conditions): the endpoint ready\ncondition will be set to false, so load balancers will not use the Pod for\nregular traffic. See [Pod termination](/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination)\nfor more information about how the kubelet handles Pod deletion.\n\n## When to use each probe {#when-to-use-each-probe}\n\n### When should you use a startup probe? {#when-should-you-use-a-startup-probe}\n\nStartup probes are useful for Pods that have containers that take a long time to\ncome into service. Rather than set a long liveness interval, you can configure a\nseparate configuration for probing the container as it starts up, allowing a\ntime longer than the liveness interval would allow.", "source": "kubernetes", "doc_type": "vendor_doc", "layer": "orchestration", "url": "https://github.com/kubernetes/website/blob/256a1f49419171f6c7fbdb1857146da1c63eb533/content/en/docs/concepts/workloads/pods/probes.md", "title": "Liveness, Readiness, and Startup Probes", "section": ""}

# [orch-01] KubePodCrashLooping is firing for one of our pods. What does it mean, and what s...   answering passage in top 3: True
#    0.815  runbooks:content/runbooks/kubernetes/KubePodCrashLooping.md#0   § 
#    0.629  runbooks:content/runbooks/alertmanager/AlertmanagerClusterCrashlooping   § 
#    0.565  runbooks:content/runbooks/kubernetes/KubePodNotReady.md#0   § 


{"chunk_id": "runbooks:content/runbooks/kubernetes/KubePodCrashLooping.md#0", "doc_id": "runbooks:content/runbooks/kubernetes/KubePodCrashLooping.md", "text": "# KubePodCrashLooping\n\n## Meaning\n\nPod is in CrashLoop which means the app dies or is unresponsive and\nkubernetes tries to restart it automatically.\n\n## Impact\n\nService degradation or unavailability.\nInability to do rolling upgrades.\nCertain apps will not perform required tasks such as data migrations.\n\n## Diagnosis\n\n- Check template via `kubectl -n $NAMESPACE get pod $POD`.\n- Check pod events via `kubectl -n $NAMESPACE describe pod $POD`.\n- Check pod logs via `kubectl -n $NAMESPACE logs $POD -c $CONTAINER`\n- Check pod template parameters such as:\n  - pod priority\n  - resources - maybe it tries to use unavailable resource, such as GPU but\n    there is limited number of nodes with GPU\n  - readiness and liveness probes may be incorrect - wrong port or command,\n    check is failing too fast due to short timeout for response\n\nOther things to check:\n\n- app responding extremely slow due to resource constraints such as memory too\n  low, not enough CPU which is required on start\n- app waits for other services to start, such as database\n- misconfiguration causing app crash on start\n- missing files such as configmaps/secrets/volumes\n- read only filesystem\n- wrong user permissions in container\n- lack of special container capabilities (securityContext)\n- app is executed in different directory than expected\n  (for example WORKDIR from Docerkfile is not used in OpenShift)\n\n## Mitigation\n\nTalk with developers or read documentation about the app, ensure to define\nsane default values to start the app.\n\nSee [Debugging Pods](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-application/#debugging-pods)", "source": "runbooks", "doc_type": "runbook", "layer": "orchestration", "url": "https://github.com/prometheus-operator/runbooks/blob/a685d14cf5128bb30e2bf935c3983decd772d885/content/runbooks/kubernetes/KubePodCrashLooping.md", "title": "Kube Pod Crash Looping", "section": ""}

# [orch-05] We got a warning that a node's root filesystem is predicted to run out of space ...   answering passage in top 3: True
#    0.720  runbooks:content/runbooks/node/NodeFilesystemAlmostOutOfSpace.md#0   §  ← wrong alert (usage already almost full)
#    0.701  runbooks:content/runbooks/node/NodeFilesystemAlmostOutOfFiles.md#0   §  ← wrong alert (inodes, not space)
#    0.695  runbooks:content/runbooks/node/NodeFilesystemSpaceFillingUp.md#0   §  ← the one that matches "predicted to run out within a day"

{"chunk_id": "runbooks:content/runbooks/node/NodeFilesystemAlmostOutOfSpace.md#0", "doc_id": "runbooks:content/runbooks/node/NodeFilesystemAlmostOutOfSpace.md", "text": "# NodeFilesystemAlmostOutOfSpace\n\n## Meaning\n\nThis alert is similar to the NodeFilesystemSpaceFillingUp alert, but rather\nthan being based on a prediction that a filesystem will become full in a certain\namount of time, it uses simple static thresholds. The alert will fire as at a\n`warning` level at 5% space left, and at a `critical` level with 3% space left.\n\n## Impact\n\nA node's filesystem becoming full can have a far reaching impact, as it may\ncause any or all of the applications scheduled to that node to experience\nanything from performance degradation to full inoperability. Depending on the\nnode and filesystem involved, this could pose a critical threat to the stability\nof the cluster.\n\n## Diagnosis\n\n## Mitigation\n\nSee Node Filesystem FilesFilling Up", "source": "runbooks", "doc_type": "runbook", "layer": "orchestration", "url": "https://github.com/prometheus-operator/runbooks/blob/a685d14cf5128bb30e2bf935c3983decd772d885/content/runbooks/node/NodeFilesystemAlmostOutOfSpace.md", "title": "Node Filesystem Almost Out Of Space", "section": ""}

# ok: layer='database' filter respected (5 hits, all database)
# ok: asking for postmortems on a Phase A index returns 0 hits (none are loaded yet)

# not-in-corpus question (na-04, Kong): top scores [0.383, 0.344, 0.339]  <- it still returns 3 chunks
# real question (db-01):               top score  0.706

# all retrieval checks passed
