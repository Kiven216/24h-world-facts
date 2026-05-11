function RefreshButton({ loading, onRefresh, label = 'Refresh' }) {
  return (
    <button
      type="button"
      className="refresh-button refresh-icon-button"
      onClick={onRefresh}
      disabled={loading}
      aria-label="Refresh feed"
      title="Refresh feed"
    >
      <span className={`refresh-icon ${loading ? 'refresh-icon-spinning' : ''}`.trim()} aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path
            d="M20 12a8 8 0 1 1-2.35-5.66"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M20 4v4h-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className="sr-only">{loading ? 'Refreshing feed' : label}</span>
    </button>
  );
}

export default RefreshButton;
