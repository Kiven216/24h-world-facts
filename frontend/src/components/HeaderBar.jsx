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
        <h1>24H World Facts</h1>
        <p className="header-subtitle">Global Intelligence Briefing</p>
        <p className="header-updated">Updated {formatMetaTime(meta.last_updated)}</p>
      </div>
      <div className="header-side">
        {action ? <div className="header-action">{action}</div> : null}
      </div>
    </header>
  );
}

export default HeaderBar;
