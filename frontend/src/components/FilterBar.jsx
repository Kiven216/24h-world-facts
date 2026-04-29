import { useEffect, useState } from 'react';

const MOBILE_MEDIA_QUERY = '(max-width: 560px)';

function FilterBar({ filters, onFilterChange, options, summary }) {
  const [isMobile, setIsMobile] = useState(() => (typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia(MOBILE_MEDIA_QUERY).matches
    : false));
  const [isOpen, setIsOpen] = useState(() => (typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? !window.matchMedia(MOBILE_MEDIA_QUERY).matches
    : true));

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return undefined;
    }

    const mediaQuery = window.matchMedia(MOBILE_MEDIA_QUERY);
    const syncMobileState = (event) => {
      const nextIsMobile = event.matches;
      setIsMobile(nextIsMobile);
      setIsOpen(nextIsMobile ? false : true);
    };

    syncMobileState(mediaQuery);

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', syncMobileState);
      return () => mediaQuery.removeEventListener('change', syncMobileState);
    }

    mediaQuery.addListener(syncMobileState);
    return () => mediaQuery.removeListener(syncMobileState);
  }, []);

  return (
    <section className={`filter-panel ${isMobile ? 'filter-panel-mobile' : ''} ${isOpen ? 'filter-panel-open' : 'filter-panel-collapsed'}`}>
      {isMobile ? (
        <button className="filter-toggle" type="button" onClick={() => setIsOpen((currentValue) => !currentValue)}>
          <span>Filters</span>
          <span className="filter-toggle-summary">{summary}</span>
        </button>
      ) : null}

      {(!isMobile || isOpen) ? (
        <div className={`filter-bar-shell ${isMobile ? 'filter-bar-shell-mobile' : ''}`}>
          {isMobile ? <button className="filter-overlay" type="button" aria-label="Close filters" onClick={() => setIsOpen(false)} /> : null}
          <div className={`filter-bar ${isMobile ? 'filter-bar-mobile' : ''}`}>
            {isMobile ? (
              <div className="filter-mobile-header">
                <div>
                  <strong>Filters</strong>
                  <span>{summary}</span>
                </div>
                <button className="filter-close" type="button" onClick={() => setIsOpen(false)}>
                  Done
                </button>
              </div>
            ) : null}

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
        </div>
      ) : null}
    </section>
  );
}

export default FilterBar;
