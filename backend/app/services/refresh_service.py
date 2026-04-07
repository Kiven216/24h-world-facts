"""Run the current multi-source refresh chain in sequence."""

from ..pipelines.filter import run_filter
from ..pipelines.ingest import run_ingest
from ..pipelines.normalize import run_normalize
from ..pipelines.publish import run_publish


def trigger_refresh() -> dict[str, object]:
    ingest_result = run_ingest()
    normalize_result = run_normalize()
    filter_result = run_filter()
    publish_result = run_publish()

    return {
        "status": "ok",
        "steps": {
            "ingest": ingest_result,
            "normalize": normalize_result,
            "filter": filter_result,
            "publish": publish_result,
        },
    }
