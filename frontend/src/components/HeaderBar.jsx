function formatMetaTime(value) {
  if (!value) {
    return 'Unavailable';
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return parsedDate.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function HeaderBar({ meta, activeSummary }) {
  return (
    <header className="header-bar">
      <div className="header-copy-block">
        <p className="eyebrow">24-Hour Briefing</p>
        <h1>24H World Facts</h1>
        <p className="header-copy">
          A restrained homepage scaffold for important factual stories from the last {meta.window_hours} hours.
        </p>
        <p className="header-active-summary">{activeSummary}</p>
      </div>
      <div className="header-meta">
        <div className="header-meta-card">
          <span>Last updated</span>
          <strong>{formatMetaTime(meta.last_updated)}</strong>
        </div>
        <div className="header-meta-card">
          <span>Total events</span>
          <strong>{meta.total_events}</strong>
        </div>
      </div>
    </header>
  );
}

export default HeaderBar;
