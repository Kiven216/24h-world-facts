import { useEffect, useState } from 'react';

import FilterBar from '../components/FilterBar';
import HeaderBar from '../components/HeaderBar';
import HomepageDebugPanel from '../components/HomepageDebugPanel';
import RefreshButton from '../components/RefreshButton';
import SectionBlock from '../components/SectionBlock';
import StoryCard from '../components/StoryCard';
import { fetchHomeData, triggerBackendRefresh } from '../services/api';
import { mockHomeData } from '../mock/mockHomeData';

const REGION_OPTIONS = ['All', 'North America', 'Europe', 'Japan / East Asia', 'Global Markets'];
const TOPIC_OPTIONS = ['All', 'Policy / Politics', 'Economy / Markets', 'Business / Tech / Industry', 'Conflict / Security'];
const CONFIDENCE_OPTIONS = ['All', 'Official', 'Confirmed', 'Widely Reported', 'Developing', 'Monitoring'];
const SORT_OPTIONS = ['Importance', 'Latest'];
const TOPIC_SECTION_ORDER = ['Economy / Markets', 'Business / Tech / Industry', 'Policy / Politics', 'Conflict / Security'];

const DEFAULT_FILTERS = {
  region: 'All',
  topic: 'All',
  confidence: 'All',
  sortBy: 'Importance',
};

function normalizeConfidence(status) {
  const normalized = String(status || '').trim().toLowerCase();
  const confidenceMap = {
    official: 'Official',
    confirmed: 'Confirmed',
    'widely reported': 'Widely Reported',
    widely_reported: 'Widely Reported',
    developing: 'Developing',
    monitoring: 'Monitoring',
  };

  return confidenceMap[normalized] || 'Confirmed';
}

function getStoryTimestamp(story) {
  return Date.parse(story.published_at || story.updated_at || '') || 0;
}

function sortStories(stories, sortBy) {
  const sortedStories = [...stories];

  sortedStories.sort((left, right) => {
    if (sortBy === 'Latest') {
      return getStoryTimestamp(right) - getStoryTimestamp(left);
    }

    return (right.importance_score || 0) - (left.importance_score || 0);
  });

  return sortedStories;
}

function matchesFilters(story, filters) {
  const matchesRegion = filters.region === 'All' || story.region === filters.region;
  const matchesTopic = filters.topic === 'All' || story.topic === filters.topic;
  const matchesConfidence = filters.confidence === 'All' || normalizeConfidence(story.status) === filters.confidence;

  return matchesRegion && matchesTopic && matchesConfidence;
}

function filterAndSortStories(stories, filters) {
  return sortStories(stories.filter((story) => matchesFilters(story, filters)), filters.sortBy);
}

function buildGroupedStories(groupedStories, filters, category) {
  const selectedValue = category === 'region' ? filters.region : filters.topic;
  const visibleEntries = Object.entries(groupedStories).filter(([groupName]) => selectedValue === 'All' || groupName === selectedValue);
  const orderedEntries = category === 'topic'
    ? [...visibleEntries].sort(([leftName], [rightName]) => {
        const leftIndex = TOPIC_SECTION_ORDER.indexOf(leftName);
        const rightIndex = TOPIC_SECTION_ORDER.indexOf(rightName);
        const normalizedLeftIndex = leftIndex === -1 ? TOPIC_SECTION_ORDER.length : leftIndex;
        const normalizedRightIndex = rightIndex === -1 ? TOPIC_SECTION_ORDER.length : rightIndex;
        return normalizedLeftIndex - normalizedRightIndex;
      })
    : visibleEntries;

  return orderedEntries
    .map(([groupName, stories]) => [groupName, filterAndSortStories(stories, filters)])
    .filter(([, stories]) => stories.length > 0);
}

function buildActiveSummary(filters) {
  return `${filters.region} / ${filters.topic} / ${filters.confidence} / ${filters.sortBy}`;
}

function HomePage() {
  const debugEnabled = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('debug') === '1';
  const [homeData, setHomeData] = useState(mockHomeData);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const topStories = filterAndSortStories(homeData.top_stories, filters);
  const watchlistStories = filterAndSortStories(homeData.watchlist, filters);
  const regionSections = buildGroupedStories(homeData.by_region, filters, 'region');
  const topicSections = buildGroupedStories(homeData.by_topic, filters, 'topic');

  const handleFilterChange = (field, value) => {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [field]: value,
    }));
  };

  const loadHomeData = async ({ isManualRefresh = false } = {}) => {
    let refreshError = '';

    if (isManualRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      if (isManualRefresh) {
        try {
          await triggerBackendRefresh();
        } catch (requestError) {
          refreshError = requestError.message || 'Unable to refresh from BBC.';
        }
      }

      const payload = await fetchHomeData({ debug: debugEnabled });
      setHomeData(payload);
      setError(refreshError);
    } catch (requestError) {
      setError(requestError.message || 'Unable to load homepage data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadHomeData();
  }, [debugEnabled]);

  return (
    <div className="page-shell">
      <div className="page-backdrop" />
      <main className="page-content">
        <HeaderBar
          meta={homeData.meta}
          action={<RefreshButton loading={refreshing} onRefresh={() => loadHomeData({ isManualRefresh: true })} label="Refresh feed" />}
        />

        <div className="toolbar-row">
          <FilterBar
            filters={filters}
            onFilterChange={handleFilterChange}
            summary={buildActiveSummary(filters)}
            options={{
              region: REGION_OPTIONS,
              topic: TOPIC_OPTIONS,
              confidence: CONFIDENCE_OPTIONS,
              sortBy: SORT_OPTIONS,
            }}
          />
        </div>

        {error ? <div className="status-banner">Latest refresh notice: {error}</div> : null}
        {loading ? <div className="status-banner">Loading latest homepage data...</div> : null}

        <SectionBlock
          title="Top Stories"
          subtitle="Most important items for the current 24-hour window."
          className="section-block-featured section-block-bare"
        >
          {topStories.length > 0 ? (
            <div className="top-stories-grid">
              {topStories.map((story, index) => (
                <StoryCard
                  key={story.event_id}
                  story={story}
                  compact={index > 0}
                  variant={index === 0 ? 'lead' : 'supporting'}
                />
              ))}
            </div>
          ) : null}
        </SectionBlock>

        <SectionBlock
          title="By Topic"
          subtitle="Policy, market, business, and security lenses."
          className="section-block-minimal"
        >
          {topicSections.length > 0 ? (
            <div className="group-stack">
              {topicSections.map(([topic, stories]) => (
                <section key={topic} className="subsection-block">
                  <div className="subsection-heading">
                    <h3>{topic}</h3>
                    <span>{stories.length} stories</span>
                  </div>
                  <div className="story-grid">
                    {stories.map((story) => (
                      <StoryCard key={`${topic}-${story.event_id}`} story={story} compact />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : null}
        </SectionBlock>

        <SectionBlock
          title="By Region"
          subtitle="Regional grouping with limited overlap by design."
          className="section-block-minimal"
        >
          {regionSections.length > 0 ? (
            <div className="group-stack">
              {regionSections.map(([region, stories]) => (
                <section key={region} className="subsection-block">
                  <div className="subsection-heading">
                    <h3>{region}</h3>
                    <span>{stories.length} stories</span>
                  </div>
                  <div className="story-grid">
                    {stories.map((story) => (
                      <StoryCard key={`${region}-${story.event_id}`} story={story} compact />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : null}
        </SectionBlock>

        <SectionBlock
          title="Watchlist"
          subtitle="Items worth monitoring for follow-through or second-order impact."
          className="section-block-watchlist"
        >
          {watchlistStories.length > 0 ? (
            <div className="story-grid">
              {watchlistStories.map((story) => (
                <StoryCard key={`watch-${story.event_id}`} story={story} />
              ))}
            </div>
          ) : null}
        </SectionBlock>

        {debugEnabled ? <HomepageDebugPanel debug={homeData.debug} /> : null}
      </main>
    </div>
  );
}

export default HomePage;
