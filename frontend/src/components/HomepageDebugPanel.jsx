function HomepageDebugPanel({ debug }) {
  if (!debug) {
    return null;
  }

  const summary = debug.summary || {};
  const selectedTopStories = debug.selected_top_stories || [];
  const suppressed = debug.suppressed || [];

  return (
    <details className="homepage-debug-panel">
      <summary>Debug · Homepage selection</summary>

      <div className="homepage-debug-content">
        <section className="homepage-debug-section">
          <h3>Summary</h3>
          <ul className="homepage-debug-summary">
            <li>Selected top stories: {summary.selected_top_count || 0}</li>
            <li>Suppressed: {summary.suppressed_count || 0}</li>
            <li>Selected after fallback: {summary.selected_after_fallback_count || 0}</li>
            <li>Strong: {summary.strong_same_event_count || 0}</li>
            <li>Moderate: {summary.moderate_same_event_count || 0}</li>
          </ul>
        </section>

        <section className="homepage-debug-section">
          <h3>Selected Top Stories</h3>
          <div className="homepage-debug-list">
            {selectedTopStories.map((story) => (
              <article key={`selected-${story.event_id}`} className="homepage-debug-item">
                <strong>{story.source} · {story.headline}</strong>
                <span>{story.topic} · score {Number(story.score || 0).toFixed(1)}</span>
                {story.anchors?.length ? <span>anchors: {story.anchors.join(', ')}</span> : null}
                {story.event_key ? <span className="homepage-debug-key">event key: {story.event_key}</span> : null}
              </article>
            ))}
          </div>
        </section>

        <section className="homepage-debug-section">
          <h3>Suppression / Fallback Decisions</h3>
          <div className="homepage-debug-list">
            {suppressed.map((item, index) => (
              <article key={`${item.bucket}-${item.candidate.event_id}-${index}`} className="homepage-debug-item">
                <strong>{item.candidate.source} · {item.candidate.headline}</strong>
                <span>{item.bucket} · {item.reason}</span>
                {item.match_class ? <span>class: {item.match_class}</span> : null}
                {item.match_rule ? <span>rule: {item.match_rule}</span> : null}
                {item.action ? <span>action: {item.action}</span> : null}
                <span>matched: {item.matched_reference.source} · {item.matched_reference.headline}</span>
                {item.shared_anchors?.length ? <span>anchors: {item.shared_anchors.join(', ')}</span> : null}
                {item.event_key ? <span className="homepage-debug-key">event key: {item.event_key}</span> : null}
              </article>
            ))}
          </div>
        </section>
      </div>
    </details>
  );
}

export default HomepageDebugPanel;
