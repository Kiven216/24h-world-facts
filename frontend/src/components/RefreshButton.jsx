function RefreshButton({ loading, onRefresh }) {
  return (
    <button type="button" className="refresh-button" onClick={onRefresh} disabled={loading}>
      {loading ? 'Refreshing...' : 'Refresh'}
    </button>
  );
}

export default RefreshButton;
