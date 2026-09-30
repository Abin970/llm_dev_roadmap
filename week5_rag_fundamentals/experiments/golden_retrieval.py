"""golden_retrieval -- fixed questions with known answering passages, for
measuring retrieval (exercises 1-3; Weeks 6-7 reuse the same set).

This set was written AFTER the corpus was fetched, by reading the real
pages. Every expected doc_id, section, marker and key fact below was
checked against the fetched text on 2026-09-30. Nothing in the corpus
was written or picked to make these questions answerable; that's the
difference from Week 4's eval_cases.

How a retrieved chunk is judged:
    a chunk HITS an Expected entry  <=>  chunk.doc_id == expected.doc_id
                                         AND any marker appears in chunk.text
    (case-insensitive, with whitespace collapsed on both sides)
Markers are short verbatim phrases from the passage that answers the
question. So a hit means "the answering passage is inside this chunk",
not just "some chunk from the right page". That's what makes hit@k
sensitive to chunking (exercise 2): a strategy that cuts the passage in
half can lose the marker.

Kinds:
    identifier     names the exact alert / setting / metric (keyword
                   search should do well here)
    symptom        describes what the on-call engineer SEES, without the
                   name (the case dense retrieval exists for)
    cross_source   needs passages from two sources (needs_all=True: every
                   Expected entry must be hit)
    not_in_corpus  nothing in the corpus answers it; the right behavior
                   is saying so, with no citation

`key_facts` is what a correct answer says, quoted or closely paraphrased
from the source. Checking final answers against it is Week 7's LLM-judge
work; this week only measures whether retrieval found the passage. The
user verifies answer correctness independently (their call, 2026-09-30).

Plumbing/fixture, not a TODO. Add questions freely, but write them from
pages you've actually read, with markers copied verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass

import _bootstrap  # noqa: F401  (puts assistant/ on sys.path)
from ingestion.sources import SOURCES

_SOURCE_PHASE = {s.name: s.phase for s in SOURCES}


@dataclass(frozen=True)
class Expected:
    doc_id: str
    markers: tuple[str, ...]
    section: str = ""          # human pointer only; not used for scoring


@dataclass(frozen=True)
class GoldenQuestion:
    qid: str
    question: str
    kind: str                  # identifier | symptom | cross_source | not_in_corpus
    layer: str                 # primary layer (ingestion.sources.LAYERS)
    expected: tuple[Expected, ...]
    key_facts: str
    needs_all: bool = False    # cross_source: every Expected must be hit

    @property
    def phase(self) -> str:
        """"A" if the question is answerable from Phase A sources alone
        (any expected doc for an any-match question, every one for a
        needs_all question). not_in_corpus questions count as "A", since
        they apply to any index."""
        phases = [_SOURCE_PHASE[e.doc_id.split(":", 1)[0]] for e in self.expected]
        if not phases:
            return "A"
        if self.needs_all:
            return "A" if all(p == "A" for p in phases) else "B"
        return "A" if "A" in phases else "B"


def E(doc_id: str, *markers: str, section: str = "") -> Expected:
    return Expected(doc_id, markers, section)


GOLDEN: tuple[GoldenQuestion, ...] = (
    # ---------------------------------------------------------------- database
    GoldenQuestion(
        "db-01", "What does idle_in_transaction_session_timeout do in PostgreSQL, and what's its default?",
        "identifier", "database",
        (E("postgres:runtime-config-client", "within an open transaction for longer than",
           section="19.11.1. Statement Behavior"),),
        "Terminates any session that has been idle (waiting for a client query) inside an open "
        "transaction for longer than the set time. 0, the default, disables it. It keeps idle "
        "sessions from holding locks, and open transactions also block vacuum from removing dead rows.",
    ),
    GoldenQuestion(
        "db-02", "Postgres started rejecting every INSERT and UPDATE with a hint to run a database-wide "
        "VACUUM, while SELECTs still work. What state is the database in, and how do we get out of it?",
        "symptom", "database",
        (E("postgres:routine-vacuuming", "not accepting commands that assign new transaction IDs",
           "fewer than three million transactions left",
           section="24.1.5. Preventing Transaction ID Wraparound Failures"),),
        "Transaction ID wraparound protection: with fewer than three million XIDs left, Postgres refuses "
        "to assign new XIDs, so only read-only transactions can start. A manual database-wide VACUUM "
        "(run as superuser) is the way out.",
    ),
    GoldenQuestion(
        "db-03", "A migration that only added a column hung, and while it waited every SELECT on that "
        "table started timing out too. Why would a schema change block plain reads?",
        "symptom", "database",
        (E("postgres:explicit-locking", "Conflicts with locks of all modes",
           "the only transaction accessing the table in any way", section="13.3.1. Table-Level Locks"),),
        "Many ALTER TABLE forms take an ACCESS EXCLUSIVE lock, which conflicts with every lock mode, "
        "including the ACCESS SHARE lock a SELECT takes. So reads queue behind the migration's lock request.",
    ),
    GoldenQuestion(
        "db-04", "What does max_connections control in PostgreSQL, and can it be changed without a restart?",
        "identifier", "database",
        (E("postgres:runtime-config-connection", "Determines the maximum number of concurrent connections",
           section="19.3.1. Connection Settings"),),
        "The maximum number of concurrent connections, typically 100 by default. It can only be set at "
        "server start, and on a standby it must be at least the primary's value.",
    ),
    # ----------------------------------------------------------- orchestration
    GoldenQuestion(
        "orch-01", "KubePodCrashLooping is firing for one of our pods. What does it mean, and what should "
        "we check first?",
        "identifier", "orchestration",
        (E("runbooks:content/runbooks/kubernetes/KubePodCrashLooping.md", "the app dies or is unresponsive",
           section="Meaning / Diagnosis"),),
        "The app keeps dying or not responding and Kubernetes keeps restarting it. Check the pod with "
        "kubectl get/describe (events) and logs, then its template: priority, resources, and "
        "liveness/readiness probes (wrong port or command).",
    ),
    GoldenQuestion(
        "orch-02", "A container keeps getting killed and restarted when traffic peaks, and its memory graph "
        "climbs right before each kill. What is killing it?",
        "symptom", "orchestration",
        (E("kubernetes:content/en/docs/concepts/configuration/manage-resources-containers.md",
           "out of memory (OOM) kills", section="Requests and limits"),),
        "Memory limits are enforced by the kernel with OOM kills: a container using more than its memory "
        "limit may be terminated. This is enforced reactively, when the kernel detects memory pressure.",
    ),
    GoldenQuestion(
        "orch-03", "Pods on one node keep getting evicted even though their own usage looks normal. How "
        "does the kubelet decide that a node is short on memory?",
        "symptom", "orchestration",
        (E("kubernetes:content/en/docs/concepts/scheduling-eviction/node-pressure-eviction.md",
           "memory.available", "has satisfied an eviction threshold", section="Eviction signals / Node conditions"),),
        "The kubelet watches eviction signals such as memory.available (capacity minus working set). When "
        "one crosses an eviction threshold, the node gets the MemoryPressure condition and the kubelet "
        "evicts pods to reclaim memory.",
    ),
    GoldenQuestion(
        "orch-04", "What's the difference between a failing liveness probe and a failing readiness probe?",
        "identifier", "orchestration",
        (E("kubernetes:content/en/docs/concepts/workloads/pods/probes.md",
           "Liveness probes determine when to restart a container",
           "Readiness probes determine when a container is ready to accept traffic",
           section="Liveness probe / Readiness probe"),),
        "A failed liveness probe makes the kubelet restart the container. A failed readiness probe only "
        "takes the pod out of service endpoints (no traffic) without restarting it.",
    ),
    GoldenQuestion(
        "orch-05", "We got a warning that a node's root filesystem is predicted to run out of space within "
        "a day. Which alert is this, and how is it mitigated?",
        "symptom", "orchestration",
        (E("runbooks:content/runbooks/node/NodeFilesystemSpaceFillingUp.md",
           "based on an extrapolation of the space used", section="Meaning / Mitigation"),),
        "NodeFilesystemSpaceFillingUp: fires when usage is over a threshold AND the extrapolation predicts "
        "running out (warning under 24h, critical under 4h). For /, /sysroot or /var mountpoints, remove "
        "unused images via kubectl debug on the node. The distractor is NodeFilesystemAlmostOutOfSpace.",
    ),
    # -------------------------------------------------------------- gateway_lb
    GoldenQuestion(
        "gw-01", "We created an Ingress resource for a new service, but nothing routes to it and there are "
        "no errors anywhere. What's the most basic thing that could be missing?",
        "symptom", "gateway_lb",
        (E("kubernetes:content/en/docs/concepts/services-networking/ingress.md",
           "Only creating an Ingress resource has no effect", section="Prerequisites"),),
        "An Ingress controller. The Ingress resource alone does nothing; a controller must be running "
        "to satisfy it.",
    ),
    GoldenQuestion(
        "gw-02", "In an nginx upstream block, what do max_fails and fail_timeout do, and what are their "
        "defaults?",
        "identifier", "gateway_lb",
        (E("nginx:ngx_http_upstream_module", "number of unsuccessful attempts to communicate with the server",
           "By default, the parameter is set to 10 seconds", section="Directives (server)"),),
        "max_fails (default 1, 0 disables) unsuccessful attempts within fail_timeout mark the server "
        "unavailable for fail_timeout (default 10s). What counts as unsuccessful is defined by "
        "proxy_next_upstream.",
    ),
    GoldenQuestion(
        "gw-03", "Users get a 504 from nginx on a report endpoint that takes about 90 seconds to respond. "
        "Which nginx setting is cutting it off?",
        "symptom", "gateway_lb",
        (E("nginx:ngx_http_proxy_module", "Defines a timeout for reading a response from the proxied server",
           section="Directives (proxy_read_timeout)"),),
        "proxy_read_timeout (default 60s). It applies between two successive reads, not to the whole "
        "response; if the upstream sends nothing for that long, the connection is closed.",
    ),
    GoldenQuestion(
        "xl-01", "During traffic bursts some clients get HTTP 503. Requests go through nginx to uvicorn. "
        "Which setting on each layer can produce a 503 like that?",
        "cross_source", "gateway_lb",
        (E("nginx:ngx_http_limit_req_module", "the maximum burst size in which case the request is terminated",
           "limit_req_status 503", section="Directives (limit_req, limit_req_status)"),
         E("uvicorn:docs/settings.md", "before issuing HTTP 503 responses", section="Resource Limits")),
        "nginx limit_req: requests beyond the burst size are rejected with limit_req_status (default 503). "
        "uvicorn --limit-concurrency: past the limit, it returns 503 immediately, without queueing.",
        needs_all=True,
    ),
    # -------------------------------------------------------------- app_server
    GoldenQuestion(
        "app-01", "What does Gunicorn's timeout setting do, and what's the default?",
        "identifier", "app_server",
        (E("gunicorn:docs/content/reference/settings.md",
           "Workers silent for more than this many seconds are killed and restarted", section="timeout"),),
        "Workers silent for longer than timeout (default 30s) are killed and restarted; 0 disables it. "
        "The distractor is dirty_timeout, which has similar wording but applies to dirty workers.",
    ),
    GoldenQuestion(
        "app-02", "How many Gunicorn workers should we start with?",
        "identifier", "app_server",
        (E("gunicorn:docs/content/design.md", "(2 × CPU cores) + 1", "4–12 workers", section="How Many Workers?"),),
        "Start from (2 × CPU cores) + 1 and adjust under load. Gunicorn typically needs only 4-12 workers "
        "even for heavy traffic, and too many waste resources.",
    ),
    GoldenQuestion(
        "app-03", "What does uvicorn's --timeout-keep-alive default to?",
        "identifier", "app_server",
        (E("uvicorn:docs/settings.md", "Close Keep-Alive connections if no new data is received",
           section="Timeouts"),),
        "5 seconds. Keep-alive connections are closed if no new data arrives within the timeout.",
    ),
    GoldenQuestion(
        "xl-02", "Our Gunicorn app sits behind nginx, and we see sporadic errors on reused idle keep-alive "
        "connections. What do the Gunicorn and nginx docs each say about idle keep-alive, and why could "
        "their defaults clash?",
        "cross_source", "app_server",
        (E("gunicorn:docs/content/reference/settings.md", "When Gunicorn is deployed behind a load balancer",
           section="keepalive"),
         E("nginx:ngx_http_upstream_module", "idle keepalive connection to an upstream server will stay open",
           section="Directives (keepalive_timeout)")),
        "Gunicorn keepalive defaults to 2s, and its docs say to set it higher behind a load balancer. "
        "nginx's upstream keepalive_timeout keeps idle upstream connections open for 60s by default. "
        "Neither doc states the clash: nginx can reuse a connection Gunicorn has already closed.",
        needs_all=True,
    ),
    # ------------------------------------------------------------------- cache
    GoldenQuestion(
        "cache-01", "What happens when Redis reaches maxmemory under the noeviction policy?",
        "identifier", "cache",
        (E("redis:content/develop/reference/eviction/index.md",
           "Keys are not evicted but the server will return an error", section="Eviction policies"),),
        "Nothing is evicted: commands that would store new data return an error, while commands that only "
        "read existing data keep working. With replication, this applies to the primary.",
    ),
    GoldenQuestion(
        "cache-02", "Redis latency spikes periodically on a Linux VM even though no slow commands show up. "
        "Which system-level things does Redis recommend checking first?",
        "symptom", "cache",
        (E("redis:content/operate/oss_and_stack/management/optimization/latency.md",
           "Transparent huge pages must be disabled", section="Diagnosing latency issues (checklist)"),),
        "The checklist: use the slow log to rule out blocking commands; on EC2 use HVM instances, or fork() "
        "is too slow; disable transparent huge pages; measure the VM's intrinsic latency with "
        "redis-cli --intrinsic-latency.",
    ),
    GoldenQuestion(
        "cache-03", "After we shortened a cache TTL, the database got overloaded at the next weekday peak. "
        "Has anyone written up an incident like this?",
        "symptom", "cache",
        (E("postmortems:github-cache-ttl-read-traffic", "from 12 to 2 hours", section="February 9 incident"),),
        "GitHub cut a user-settings cache refresh TTL from 12 to 2 hours on a quiet weekend. At the Monday "
        "peak, with client read traffic already growing, the extra load overwhelmed the backing store.",
    ),
    # ----------------------------------------------------------- message_queue
    GoldenQuestion(
        "mq-01", "How do min.insync.replicas and the producer's acks setting work together in Kafka?",
        "identifier", "message_queue",
        (E("kafka:content/en/43/design/design.md", "minimum number of in-sync replicas", section="Replication"),),
        "With acks=all, the write is acknowledged only once the in-sync replica set has it, and the "
        "topic's min.insync.replicas sets how many in-sync replicas must exist for that. acks=1 waits for "
        "the leader only; acks=0 doesn't wait.",
    ),
    GoldenQuestion(
        "mq-02", "One consumer group keeps falling further behind the producers. Which consumer metric "
        "shows how far behind it is?",
        "symptom", "message_queue",
        (E("kafka:content/en/43/operations/monitoring.md", "lags behind the producer", section="Monitoring (consumer metrics)"),),
        "records-lag-max (kafka.consumer:type=consumer-fetch-manager-metrics): the number of messages the "
        "consumer lags behind the producer. It's published by the consumer, not the broker.",
    ),
    GoldenQuestion(
        "mq-03", "After a routine RabbitMQ upgrade, long-running consumers started getting disconnected "
        "and their messages redelivered. Has this happened to anyone else?",
        "symptom", "message_queue",
        (E("postmortems:circleci-2021-rabbitmq-ack-timeout", "15 minute acknowledgment timeout",
           section="Contributing Event"),),
        "CircleCI, May 2021: a RabbitMQ 3.8 upgrade introduced a 15-minute consumer acknowledgment timeout. "
        "The changelog described it as applying to quorum queues only, but it applied to all queue types.",
    ),
    # --------------------------------------------------------------- container
    GoldenQuestion(
        "ctr-01", "What's the difference between Docker's always and unless-stopped restart policies?",
        "identifier", "container",
        (E("docker:content/manuals/engine/containers/start-containers-automatically.md",
           "it isn't restarted even after Docker daemon restarts", section="Use a restart policy"),),
        "unless-stopped behaves like always, except that a container that was stopped (manually or "
        "otherwise) is not restarted, even when the Docker daemon restarts.",
    ),
    GoldenQuestion(
        "ctr-02", "The whole Docker host became unresponsive after one container used a lot of memory. How "
        "does Docker deal with the host running out of memory?",
        "symptom", "container",
        (E("docker:content/manuals/engine/containers/resource_constraints.md", "Out Of Memory Exception",
           section="Understand the risks of running out of memory"),),
        "The Linux kernel throws an OOME and starts killing processes, and any process can be killed, "
        "including Docker itself. Docker lowers the daemon's OOM priority but not the containers'. Set "
        "memory limits on containers.",
    ),
    # ------------------------------------------------------------- logs_config
    GoldenQuestion(
        "logs-01", "We changed a value in a ConfigMap, but the running pods still see the old value in "
        "their environment variables. Why?",
        "symptom", "logs_config",
        (E("kubernetes:content/en/docs/concepts/configuration/configmap.md",
           "consumed as environment variables are not updated automatically",
           section="Mounted ConfigMaps are updated automatically"),),
        "ConfigMaps consumed as environment variables are not updated automatically; the pod must be "
        "restarted. Mounted-volume ConfigMaps do update, after a sync delay.",
    ),
    GoldenQuestion(
        "logs-02", "A host's disk keeps filling up with container logs from Docker's default logging "
        "driver. How do we cap it?",
        "symptom", "logs_config",
        (E("docker:content/manuals/engine/logging/drivers/json-file.md", "to enable automatic log-rotation",
           section="Usage"),),
        "Set log-opts max-size and max-file for the json-file driver in daemon.json (values must be "
        "strings), then restart Docker. It only applies to newly created containers.",
    ),
    GoldenQuestion(
        "logs-03", "Under heavy load, Fluent Bit stops reading a log file for a while and catches up later. "
        "Which setting causes that pause?",
        "symptom", "logs_config",
        (E("fluentbit:pipeline/inputs/tail.md", "If the limit is reached, it will be paused",
           section="Configuration parameters"),
         E("fluentbit:administration/backpressure.md",
           "enforce a limit for how much data that plugin can buffer to memory",
           section="Set mem_buf_limit for input plugins")),
        "mem_buf_limit: once an input plugin's memory buffer hits the limit, the input is paused until "
        "data is flushed. With memory-only buffering some inputs can lose data; filesystem buffering "
        "avoids that.",
    ),
    # ----------------------------------------------------------- observability
    GoldenQuestion(
        "obs-01", "AlertmanagerFailedToSendAlerts is firing. Is anything actually broken?",
        "identifier", "observability",
        (E("runbooks:content/runbooks/alertmanager/AlertmanagerFailedToSendAlerts.md", "unable to routed alert",
           section="Meaning / Impact"),),
        "At least one Alertmanager instance can't deliver to an integration. There's no impact, since "
        "another instance should send the notification, unless AlertmanagerClusterFailedToSendAlerts "
        "also fires for the same integration.",
    ),
    GoldenQuestion(
        "obs-02", "How does PromQL's increase() handle a counter that resets when the target restarts?",
        "identifier", "observability",
        (E("prometheus:docs/querying/functions.md", "counter resets due to target restarts", section="increase()"),),
        "Breaks in monotonicity such as counter resets are adjusted for automatically. The result is "
        "extrapolated over the whole range, so it can be non-integer.",
    ),
    GoldenQuestion(
        "obs-03", "What does the Prometheus documentation recommend we alert on?",
        "identifier", "observability",
        (E("prometheus-docs:docs/practices/alerting.md", "alert on symptoms", section="(introduction)"),),
        "Keep alerting simple, alert on symptoms, have good consoles to pinpoint causes, and avoid pages "
        "where there is nothing to do.",
    ),
    GoldenQuestion(
        "obs-04", "Why would we need tail sampling instead of head sampling for OpenTelemetry traces?",
        "identifier", "observability",
        (E("otel:content/en/docs/concepts/sampling/index.md", "you need tail sampling",
           "considering all or most of the spans", section="Head Sampling / Tail Sampling"),),
        "Head sampling decides before the trace is complete, so it can't guarantee that, for example, "
        "every trace containing an error is kept. Tail sampling decides after seeing all or most spans "
        "of the trace.",
    ),
    # ---------------------------------------------------- cross-source, database
    GoldenQuestion(
        "xl-03", "A Postgres schema migration once took an app down by blocking queries. What setting do "
        "teams put on migrations to prevent it, and what does Postgres say that setting does?",
        "cross_source", "database",
        (E("postmortems:gocardless-postgres-migration-locks", "in your migration scripts", section="Avoiding downtime"),
         E("postgres:runtime-config-client", "while attempting to acquire a lock",
           section="19.11.1. Statement Behavior")),
        "Set lock_timeout in migration scripts (GoCardless: better to abort a deploy than take the app "
        "down). Postgres: lock_timeout aborts any statement that waits longer than the limit to acquire "
        "a lock, applied separately to each lock attempt.",
        needs_all=True,
    ),
    # ---------------------------------------------------------- not in corpus
    GoldenQuestion(
        "na-01", "How do we increase the WiredTiger cache size on our MongoDB replica set?",
        "not_in_corpus", "database", (),
        "Not covered: the corpus has no MongoDB docs. A correct answer says so and cites nothing.",
    ),
    GoldenQuestion(
        "na-02", "What's the default visibility timeout of an SQS queue, and how do we extend it for slow "
        "consumers?",
        "not_in_corpus", "message_queue", (),
        "Not covered: no SQS docs. The Kafka and RabbitMQ material is not a substitute.",
    ),
    GoldenQuestion(
        "na-03", "How do we rotate the root token in HashiCorp Vault?",
        "not_in_corpus", "logs_config", (),
        "Not covered: no Vault docs. The Kubernetes Secret pages are a plausible-looking distractor.",
    ),
    GoldenQuestion(
        "na-04", "How do we configure the rate-limiting plugin on our Kong API gateway?",
        "not_in_corpus", "gateway_lb", (),
        "Not covered: the corpus has NGINX rate limiting (limit_req), not Kong. A correct answer says Kong "
        "isn't covered instead of presenting NGINX settings as Kong's. This is the strongest distractor "
        "in the set.",
    ),
)


def for_phase(phase: str | None) -> list[GoldenQuestion]:
    """The questions answerable with the given phase's index ("A" = only
    Phase A sources ingested). None = every question."""
    if phase is None or phase == "B":
        return list(GOLDEN)
    return [q for q in GOLDEN if q.phase == "A"]


if __name__ == "__main__":
    from collections import Counter
    print(f"{len(GOLDEN)} questions | phase A: {len(for_phase('A'))}")
    print("by kind:", dict(Counter(q.kind for q in GOLDEN)))
    print("by layer:", dict(Counter(q.layer for q in GOLDEN)))
