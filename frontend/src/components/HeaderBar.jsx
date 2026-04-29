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

function HeaderBar({ meta, action = null }) {
  return (
    <header className="header-bar">
      <div className="header-copy-block">
        <p className="eyebrow">24-Hour Briefing</p>
        <h1>24H World Facts</h1>
      </div>
      <div className="header-side">
        <div className="header-meta">
          <div className="header-meta-card">
            <span>Last updated</span>
            <strong>{formatMetaTime(meta.last_updated)}</strong>
          </div>
        </div>
        {action ? <div className="header-action">{action}</div> : null}
      </div>
    </header>
  );
}

export default HeaderBar;
