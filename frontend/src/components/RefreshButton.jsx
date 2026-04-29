function RefreshButton({ loading, onRefresh, label = 'Refresh' }) {
  return (
    <button type="button" className="refresh-button" onClick={onRefresh} disabled={loading}>
      {loading ? 'Refreshing...' : label}
    </button>
  );
}

export default RefreshButton;
