function FilterBar({ filters, onFilterChange, options }) {
  return (
    <div className="filter-bar">
      <label className="filter-control">
        <span className="filter-label">Region</span>
        <select value={filters.region} onChange={(event) => onFilterChange('region', event.target.value)}>
          {options.region.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-control">
        <span className="filter-label">Topic</span>
        <select value={filters.topic} onChange={(event) => onFilterChange('topic', event.target.value)}>
          {options.topic.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-control">
        <span className="filter-label">Confidence</span>
        <select value={filters.confidence} onChange={(event) => onFilterChange('confidence', event.target.value)}>
          {options.confidence.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-control">
        <span className="filter-label">Sort by</span>
        <select value={filters.sortBy} onChange={(event) => onFilterChange('sortBy', event.target.value)}>
          {options.sortBy.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

export default FilterBar;
