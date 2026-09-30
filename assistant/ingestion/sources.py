"""Corpus manifest -- WHAT the SRE copilot's knowledge base contains.

The scope was fixed by one rule BEFORE any golden question was written.
The golden set is derived from these pages, never the other way round:

    For each technology in a typical production stack, include only the
    pages an on-call engineer actually opens -- configuration reference,
    operations/admin, monitoring/metrics, troubleshooting, failure/HA
    behavior. Exclude tutorials, install guides, client API references,
    release notes and contributor docs.

Three doc_types. The graph's two retrieval branches filter on them:
  - vendor_doc  official docs, "what the tool supports"  -> search_vendor_docs
  - runbook     per-alert runbooks, "what to do"         -> search_docs
  - postmortem  real public incident write-ups,
                "what happened"                          -> search_docs

Nothing fetched from here is committed (data/ is gitignored).
`python -m ingestion.fetch` (run from assistant/) re-creates data/corpus/
from this file.

Versions are pinned where the source is versioned (PostgreSQL 18, Kafka
4.3), so golden-set answers don't drift when upstream ships a new
release. Git sources are fetched at their default branch's HEAD, and
fetch.py records the exact commit in data/corpus/manifest.jsonl.

This file is plumbing -- nothing to implement here. Add or remove pages
freely, but keep the scope rule.
"""
from __future__ import annotations

from dataclasses import dataclass

LAYERS = (
    "gateway_lb", "app_server", "cache", "database", "message_queue",
    "container", "orchestration", "logs_config", "observability",
)
DOC_TYPES = ("vendor_doc", "runbook", "postmortem")


@dataclass(frozen=True)
class PathGroup:
    """Files (or directories, expanded to every file inside whose name
    doesn't start with "_") inside a git repo, all tagged with one layer."""
    layer: str
    paths: tuple[str, ...]
    fmt: str = "md"                      # "md" | "html"


@dataclass(frozen=True)
class GitSource:
    name: str                            # directory under data/corpus/raw/
    repo: str
    doc_type: str
    groups: tuple[PathGroup, ...]
    phase: str                           # "A" first slice, "B" the rest


@dataclass(frozen=True)
class WebPage:
    slug: str                            # saved as <slug>.html
    url: str
    layer: str


@dataclass(frozen=True)
class WebSource:
    name: str
    doc_type: str
    pages: tuple[WebPage, ...]
    # CSS selector of the main content element on this site. None means
    # the pages come from many different sites (postmortems), so a
    # generic main-text extractor has to find the article instead.
    content_selector: str | None
    phase: str


def _pages(base: str, layer: str, slugs: str) -> tuple[WebPage, ...]:
    return tuple(
        WebPage(slug=s, url=f"{base}{s}.html", layer=layer) for s in slugs.split()
    )


def _pm(slug: str, layer: str, url: str) -> WebPage:
    return WebPage(slug=slug, url=url, layer=layer)


SOURCES: tuple[GitSource | WebSource, ...] = (
    # ------------------------------------------------------------------
    # Phase A -- the first slice: one HTML source, one markdown source,
    # one runbook source. Enough to run exercises 1-2 end to end.
    # ------------------------------------------------------------------
    WebSource(
        name="postgres",
        doc_type="vendor_doc",
        content_selector="#docContent",
        phase="A",
        pages=_pages(
            "https://www.postgresql.org/docs/18/", "database",
            "runtime-config-connection runtime-config-resource runtime-config-wal "
            "runtime-config-replication runtime-config-logging runtime-config-autovacuum "
            "runtime-config-client runtime-config-locks runtime-config-statistics "
            "routine-vacuuming explicit-locking monitoring-stats monitoring-locks "
            "monitoring-ps wal-configuration hot-standby warm-standby kernel-resources "
            "diskusage logfile-maintenance server-shutdown using-explain pgstatstatements",
        ),
    ),
    GitSource(
        name="kubernetes",
        repo="https://github.com/kubernetes/website",
        doc_type="vendor_doc",
        phase="A",
        groups=(
            PathGroup("orchestration", tuple(
                f"content/en/docs/{p}.md" for p in (
                    "concepts/workloads/pods/pod-lifecycle",
                    "concepts/workloads/pods/probes",
                    "concepts/workloads/pods/disruptions",
                    "concepts/workloads/pods/init-containers",
                    "concepts/workloads/controllers/deployment",
                    "concepts/configuration/manage-resources-containers",
                    "concepts/scheduling-eviction/node-pressure-eviction",
                    "concepts/scheduling-eviction/pod-priority-preemption",
                    "concepts/scheduling-eviction/api-eviction",
                    "concepts/workloads/autoscaling/horizontal-pod-autoscale",
                    "concepts/workloads/autoscaling/vertical-pod-autoscale",
                    "concepts/cluster-administration/node-autoscaling",
                    "concepts/services-networking/service",
                    "tasks/configure-pod-container/configure-liveness-readiness-startup-probes",
                    "tasks/debug/debug-application/debug-pods",
                    "tasks/debug/debug-application/debug-running-pod",
                    "tasks/debug/debug-application/debug-service",
                    "tasks/debug/debug-application/debug-init-containers",
                    "tasks/debug/debug-application/determine-reason-pod-failure",
                    "tasks/debug/debug-application/debug-statefulset",
                    "tasks/debug/debug-cluster/_index",
                    "tasks/debug/debug-cluster/monitor-node-health",
                    "tasks/debug/debug-cluster/resource-metrics-pipeline",
                    "tasks/debug/debug-cluster/resource-usage-monitoring",
                    "tasks/debug/debug-cluster/troubleshoot-kubectl",
                    "tasks/debug/debug-cluster/crictl",
                    "tasks/debug/debug-cluster/kubectl-node-debug",
                )
            )),
            PathGroup("gateway_lb", (
                "content/en/docs/concepts/services-networking/ingress.md",
                "content/en/docs/concepts/services-networking/gateway.md",
            )),
            PathGroup("logs_config", (
                "content/en/docs/concepts/cluster-administration/logging.md",
                "content/en/docs/concepts/cluster-administration/system-logs.md",
                "content/en/docs/concepts/configuration/configmap.md",
                "content/en/docs/concepts/configuration/secret.md",
            )),
        ),
    ),
    GitSource(
        name="runbooks",
        repo="https://github.com/prometheus-operator/runbooks",
        doc_type="runbook",
        phase="A",
        groups=(
            PathGroup("orchestration", (
                "content/runbooks/kubernetes/",
                "content/runbooks/node/",
                "content/runbooks/etcd/",
            )),
            PathGroup("observability", (
                "content/runbooks/kube-state-metrics/",
                "content/runbooks/prometheus/",
                "content/runbooks/prometheus-operator/",
                "content/runbooks/alertmanager/",
                "content/runbooks/general/",
            )),
        ),
    ),
    # ------------------------------------------------------------------
    # Phase B -- the rest of the stack.
    # ------------------------------------------------------------------
    WebSource(
        name="nginx",
        doc_type="vendor_doc",
        content_selector="#content",
        phase="B",
        pages=(
            _pages("https://nginx.org/en/docs/", "gateway_lb", "ngx_core_module debugging_log")
            + _pages(
                "https://nginx.org/en/docs/http/", "gateway_lb",
                "load_balancing request_processing ngx_http_upstream_module "
                "ngx_http_proxy_module ngx_http_core_module ngx_http_limit_req_module "
                "ngx_http_limit_conn_module ngx_http_log_module ngx_http_stub_status_module",
            )
        ),
    ),
    GitSource(
        name="gunicorn",
        repo="https://github.com/benoitc/gunicorn",
        doc_type="vendor_doc",
        phase="B",
        groups=(PathGroup("app_server", tuple(
            f"docs/content/{p}.md" for p in (
                "reference/settings", "design", "faq", "deploy", "signals",
                "instrumentation", "configure", "guides/docker",
            )
        )),),
    ),
    GitSource(
        name="uvicorn",
        repo="https://github.com/Kludex/uvicorn",
        doc_type="vendor_doc",
        phase="B",
        groups=(PathGroup("app_server", tuple(
            f"docs/{p}.md" for p in (
                "settings", "server-behavior", "deployment/index", "deployment/docker",
                "concepts/lifespan", "concepts/logging",
            )
        )),),
    ),
    GitSource(
        name="redis",
        repo="https://github.com/redis/docs",
        doc_type="vendor_doc",
        phase="B",
        groups=(PathGroup("cache", tuple(
            f"content/{p}.md" for p in (
                "develop/reference/eviction/index",
                "develop/using-commands/keyspace",
                "commands/expire",
                "operate/oss_and_stack/management/admin",
                "operate/oss_and_stack/management/config",
                "operate/oss_and_stack/management/persistence",
                "operate/oss_and_stack/management/replication",
                "operate/oss_and_stack/management/scaling",
                "operate/oss_and_stack/management/sentinel",
                "operate/oss_and_stack/management/troubleshooting",
                "operate/oss_and_stack/management/optimization/latency",
                "operate/oss_and_stack/management/optimization/latency-monitor",
                "operate/oss_and_stack/management/optimization/memory-optimization",
            )
        )),),
    ),
    GitSource(
        name="kafka",
        repo="https://github.com/apache/kafka-site",
        doc_type="vendor_doc",
        phase="B",
        groups=(
            PathGroup("message_queue", tuple(
                f"content/en/43/{p}.md" for p in (
                    "operations/basic-kafka-operations",
                    "operations/monitoring",
                    "operations/hardware-and-os",
                    "operations/kraft",
                    "operations/consumer-rebalance-protocol",
                    "design/design",
                )
            )),
            # The configuration/*.md pages are stubs: their real content is
            # pulled in at site-build time by a Hugo shortcode,
            #   {{< include-html file="/static/{version}/generated/kafka_config.html" >}}
            # so the generated tables are listed here directly, as HTML.
            PathGroup("message_queue", tuple(
                f"content/en/43/generated/{f}.html"
                for f in ("kafka_config", "producer_config", "consumer_config", "topic_config")
            ), fmt="html"),
        ),
    ),
    GitSource(
        name="docker",
        repo="https://github.com/docker/docs",
        doc_type="vendor_doc",
        phase="B",
        groups=(
            PathGroup("container", tuple(
                f"content/manuals/engine/{p}.md" for p in (
                    "containers/resource_constraints",
                    "containers/start-containers-automatically",
                    "containers/runmetrics",
                    "daemon/troubleshoot",
                    "daemon/live-restore",
                )
            )),
            PathGroup("logs_config", tuple(
                f"content/manuals/engine/{p}.md" for p in (
                    "logging/configure",
                    "logging/dual-logging",
                    "logging/drivers/json-file",
                    "logging/drivers/local",
                    "logging/drivers/fluentd",
                    "daemon/logs",
                )
            )),
        ),
    ),
    GitSource(
        name="fluentbit",
        repo="https://github.com/fluent/fluent-bit-docs",
        doc_type="vendor_doc",
        phase="B",
        groups=(PathGroup("logs_config", tuple(
            f"{p}.md" for p in (
                "concepts/data-pipeline",
                "concepts/key-concepts",
                "pipeline/buffering",
                "pipeline/inputs/tail",
                "pipeline/filters/kubernetes",
                "administration/backpressure",
                "administration/memory-management",
                "administration/monitoring",
                "administration/performance",
                "administration/scheduling-and-retries",
                "administration/troubleshooting",
                "administration/dead-letter-queue",
                "administration/networking",
                "administration/configuring-fluent-bit/yaml/service-section",
            )
        )),),
    ),
    GitSource(
        name="prometheus-docs",
        repo="https://github.com/prometheus/docs",
        doc_type="vendor_doc",
        phase="B",
        groups=(PathGroup("observability", tuple(
            f"docs/{p}.md" for p in (
                "practices/alerting", "practices/histograms", "practices/instrumentation",
                "practices/naming", "practices/rules", "practices/remote_write",
                "concepts/data_model", "concepts/metric_types", "concepts/jobs_instances",
                "introduction/faq",
            )
        )),),
    ),
    GitSource(
        name="prometheus",
        repo="https://github.com/prometheus/prometheus",
        doc_type="vendor_doc",
        phase="B",
        groups=(PathGroup("observability", tuple(
            f"docs/{p}.md" for p in (
                "querying/basics", "querying/functions", "querying/operators",
                "querying/examples", "configuration/alerting_rules",
                "configuration/recording_rules", "storage",
            )
        )),),
    ),
    GitSource(
        name="otel",
        repo="https://github.com/open-telemetry/opentelemetry.io",
        doc_type="vendor_doc",
        phase="B",
        groups=(PathGroup("observability", tuple(
            f"content/en/docs/{p}.md" for p in (
                "concepts/observability-primer",
                "concepts/signals/traces",
                "concepts/signals/metrics",
                "concepts/signals/logs",
                "concepts/context-propagation/index",
                "concepts/sampling/index",
                "collector/architecture",
                "collector/configuration",
                "collector/resiliency",
                "collector/scaling",
                "collector/troubleshooting",
                "collector/internal-telemetry",
                "collector/deploy/agent",
                "collector/deploy/gateway",
            )
        )),),
    ),
    # Real public postmortems, picked from the danluu/post-mortems list to
    # cover every layer. The list has no license, so the pages are only
    # ever fetched, never committed. Each page's layer is its PRIMARY
    # layer -- many incidents cross layers, which is exactly what the
    # cross-layer golden questions exercise.
    #
    # Checked by extracting every page (2026-09-30). Dropped because the
    # fetched page had no usable text: Heroku status incident 2451 and
    # PagerDuty 2021-12-15 (JavaScript-only status pages), Skyliner (the
    # domain is now parked, even in the archive), and AWS Seoul DNS (the
    # listed URL is the Korean-only version). Moved links were replaced
    # with their current or web.archive.org URLs.
    WebSource(
        name="postmortems",
        doc_type="postmortem",
        content_selector=None,
        phase="B",
        pages=(
            _pm("cloudflare-2025-12-05-waf-config", "gateway_lb", "https://blog.cloudflare.com/5-december-2025-outage/"),
            _pm("cloudflare-2025-11-18-feature-file", "gateway_lb", "https://blog.cloudflare.com/18-november-2025-outage/"),
            _pm("aws-2012-elb-state-data", "gateway_lb", "https://aws.amazon.com/message/680587/"),
            _pm("github-2016-ddos-ssl-exhaustion", "gateway_lb", "https://github.blog/news-insights/the-library/denial-of-service-attacks/"),
            _pm("stackexchange-2015-load-balancers", "gateway_lb", "http://web.archive.org/web/20150404235419/https://stackstatus.net/post/115305251014/outage-postmortem-march-31-2015"),
            _pm("github-cache-ttl-read-traffic", "cache", "https://github.blog/news-insights/company-news/addressing-githubs-recent-availability-issues-2/"),
            _pm("slack-2022-02-22-cache-nodes", "cache", "https://slack.engineering/slacks-incident-on-2-22-22/"),
            _pm("incidentio-caches-connections", "cache", "https://incident.io/blog/clouds-caches-and-connection-conundrums"),
            _pm("openai-2023-03-20-redis-client", "cache", "https://web.archive.org/web/20240426015133/https://openai.com/blog/march-20-chatgpt-outage"),
            _pm("discord-redis-primary-migration", "cache", "https://status.discordapp.com/incidents/qk9cdgnqnhcn"),
            _pm("twilio-2013-billing-redis", "cache", "https://www.twilio.com/blog/2013/07/billing-incident-post-mortem-breakdown-analysis-and-root-cause.html"),
            _pm("discord-thundering-herd-oom", "app_server", "https://status.discordapp.com/incidents/dj3l6lw926kl"),
            _pm("incidentio-poison-pill-workers", "app_server", "https://incident.io/blog/intermittent-downtime"),
            _pm("spotify-2013-no-backoff-cascade", "app_server", "https://labs.spotify.com/2013/06/04/incident-management-at-spotify/"),
            _pm("sentry-2015-xid-wraparound", "database", "https://blog.sentry.io/transaction-id-wraparound-in-postgres/"),
            _pm("mandrill-xid-wraparound", "database", "https://mailchimp.com/what-we-learned-from-the-recent-mandrill-outage/"),
            _pm("joyent-2015-manta-postgres-locks", "database", "https://web.archive.org/web/20220528044329/https://www.joyent.com/blog/manta-postmortem-7-27-2015"),
            _pm("gocardless-postgres-migration-locks", "database", "https://gocardless.com/blog/zero-downtime-postgres-migrations-the-hard-parts/"),
            _pm("gocardless-db-cluster-outage", "database", "https://gocardless.com/blog/incident-review-api-and-dashboard-outage-on-10th-october/"),
            _pm("gitlab-2017-01-31-database", "database", "https://about.gitlab.com/2017/02/10/postmortem-of-database-outage-of-january-31/"),
            _pm("github-2018-10-21-mysql-failover", "database", "https://blog.github.com/2018-10-30-oct21-post-incident-analysis/"),
            _pm("incidentio-sequence-skip", "database", "https://incident.io/blog/one-two-skip-a-few"),
            _pm("circleci-2021-11-08-pg-column-type", "database", "https://discuss.circleci.com/t/incident-report-november-8-2021-jobs-stuck-in-a-not-running-state/41890"),
            _pm("incidentio-pgaudit-migration", "database", "https://status.incident.io/incidents/01JRDFKAGE07YYDY0KZR137BX3/write-up"),
            _pm("circleci-2021-rabbitmq-ack-timeout", "message_queue", "https://discuss.circleci.com/t/postmortem-may-21-2021-delay-in-starting-docker-jobs-machine-remote-docker-environments-blocked/40274"),
            _pm("github-2020-10-zookeeper-kafka", "message_queue", "https://github.blog/news-insights/company-news/github-availability-report-october-2020/"),
            _pm("aws-2020-kinesis-thread-limit", "message_queue", "https://aws.amazon.com/message/11201/"),
            _pm("aws-2024-kinesis-shards", "message_queue", "https://aws.amazon.com/message/073024/"),
            _pm("duo-request-queue-overload", "message_queue", "https://status.duo.com/incidents/4w07bmvnt359"),
            _pm("heroku-2017-container-fs-corruption", "container", "https://web.archive.org/web/2018/https://engineering.heroku.com/blogs/2017-02-15-filesystem-corruption-on-heroku-dynos/"),
            _pm("reddit-2023-pi-day-k8s-upgrade", "orchestration", "https://web.archive.org/web/20230727225235/https://www.reddit.com/r/RedditEng/comments/11xx5o0/you_broke_reddit_the_piday_outage/"),
            _pm("datadog-2023-03-08-cilium", "orchestration", "https://www.datadoghq.com/blog/2023-03-08-multiregion-infrastructure-connectivity-issue/"),
            _pm("circleci-kube-proxy-version-skew", "orchestration", "https://status.circleci.com/incidents/dcqb3fykhgvg"),
            _pm("allegro-2018-cluster-resources", "orchestration", "https://web.archive.org/web/2019/https://allegro.tech/2018/08/postmortem-why-allegro-went-down.html"),
            _pm("circleci-2025-04-04-waf-change", "logs_config", "https://discuss.circleci.com/t/post-incident-report-april-4-2025-circleci-ui-loading-build-triggering-issues/53208"),
            _pm("github-dns-puppet-manifest", "logs_config", "https://github.blog/news-insights/the-library/dns-outage-post-mortem/"),
            _pm("rust-2023-crates-dns", "logs_config", "https://blog.rust-lang.org/inside-rust/2023/02/08/dns-outage-portmortem/"),
            _pm("honeycomb-designed-failing", "observability", "https://www.honeycomb.io/blog/incident-review-designed-failing/"),
            _pm("pagerduty-2013-04-13", "observability", "https://web.archive.org/web/20211019062735/https://www.pagerduty.com/blog/outage-post-mortem-april-13-2013/"),
            _pm("cloudflare-2025-09-12-dashboard-api", "observability", "https://blog.cloudflare.com/deep-dive-into-cloudflares-sept-12-dashboard-and-api-outage/"),
        ),
    ),
)
