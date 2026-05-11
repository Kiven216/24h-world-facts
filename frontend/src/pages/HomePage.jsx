import { useEffect, useMemo, useState } from 'react';

import HeaderBar from '../components/HeaderBar';
import HomepageDebugPanel from '../components/HomepageDebugPanel';
import RefreshButton from '../components/RefreshButton';
import SectionBlock from '../components/SectionBlock';
import StoryCard from '../components/StoryCard';
import { fetchHomeData, triggerBackendRefresh } from '../services/api';
import { mockHomeData } from '../mock/mockHomeData';

const HOME_TABS = [
  { key: 'top', label: 'Top' },
  { key: 'topic', label: 'By Topic' },
  { key: 'region', label: 'By Region' },
  { key: 'watchlist', label: 'Watchlist' },
];

const TOPIC_SECTION_ORDER = ['Economy / Markets', 'Business / Tech / Industry', 'Policy / Politics', 'Conflict / Security'];

const BRIEFING_STAT_ICONS = {
  top: 'star',
  topic: 'grid',
  region: 'globe',
  watchlist: 'activity',
};

function BriefingStatIcon({ name }) {
  if (name === 'star') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 3.5l2.7 5.48 6.05.88-4.38 4.27 1.03 6.02L12 17.31l-5.4 2.84 1.03-6.02-4.38-4.27 6.05-.88L12 3.5z"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  if (name === 'grid') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4" y="4" width="6.5" height="6.5" rx="1.4" fill="none" stroke="currentColor" strokeWidth="2" />
        <rect x="13.5" y="4" width="6.5" height="6.5" rx="1.4" fill="none" stroke="currentColor" strokeWidth="2" />
        <rect x="4" y="13.5" width="6.5" height="6.5" rx="1.4" fill="none" stroke="currentColor" strokeWidth="2" />
        <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.4" fill="none" stroke="currentColor" strokeWidth="2" />
      </svg>
    );
  }

  if (name === 'globe') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth="2" />
        <ellipse cx="12" cy="12" rx="3.8" ry="8.5" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M3.5 12h17M5.6 8.1h12.8M5.6 15.9h12.8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 13h3l2.1-5.5L13 18l2.5-7h4.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function getStoryTimestamp(story) {
  return Date.parse(story.published_at || story.updated_at || '') || 0;
}

function sortStories(stories) {
  const copied = [...stories];
  copied.sort((left, right) => {
    const byScore = (right.importance_score || 0) - (left.importance_score || 0);
    if (byScore !== 0) {
      return byScore;
    }
    return getStoryTimestamp(right) - getStoryTimestamp(left);
  });
  return copied;
}

function buildTopicStories(byTopic) {
  const orderedEntries = Object.entries(byTopic || {}).sort(([left], [right]) => {
    const leftIndex = TOPIC_SECTION_ORDER.indexOf(left);
    const rightIndex = TOPIC_SECTION_ORDER.indexOf(right);
    const normalizedLeft = leftIndex === -1 ? TOPIC_SECTION_ORDER.length : leftIndex;
    const normalizedRight = rightIndex === -1 ? TOPIC_SECTION_ORDER.length : rightIndex;
    return normalizedLeft - normalizedRight;
  });

  return orderedEntries.flatMap(([topicName, stories]) =>
    sortStories(Array.isArray(stories) ? stories : []).map((story) => ({
      ...story,
      _contextLabel: topicName,
    })),
  );
}

function buildRegionStories(byRegion) {
  return Object.entries(byRegion || {}).flatMap(([regionName, stories]) =>
    sortStories(Array.isArray(stories) ? stories : []).map((story) => ({
      ...story,
      _contextLabel: regionName,
    })),
  );
}

function buildBriefingStats({ topCount, topicStoryCount, regionStoryCount, watchlistCount }) {
  return [
    {
      key: 'top',
      icon: BRIEFING_STAT_ICONS.top,
      value: topCount,
      label: 'Top Stories',
      descriptor: 'Priority',
    },
    {
      key: 'topic',
      icon: BRIEFING_STAT_ICONS.topic,
      value: topicStoryCount,
      label: 'Topics',
      descriptor: 'Coverage',
    },
    {
      key: 'region',
      icon: BRIEFING_STAT_ICONS.region,
      value: regionStoryCount,
      label: 'Regions',
      descriptor: 'Spread',
    },
    {
      key: 'watchlist',
      icon: BRIEFING_STAT_ICONS.watchlist,
      value: watchlistCount,
      label: 'Watchlist',
      descriptor: 'Follow-up',
    },
  ];
}

function HomePage() {
  const debugEnabled = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('debug') === '1';
  const [homeData, setHomeData] = useState(mockHomeData);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('top');
  const [expandedByTab, setExpandedByTab] = useState({
    top: null,
    topic: null,
    region: null,
    watchlist: null,
  });

  const topStories = useMemo(() => sortStories(Array.isArray(homeData.top_stories) ? homeData.top_stories : []), [homeData.top_stories]);
  const topicStories = useMemo(() => buildTopicStories(homeData.by_topic), [homeData.by_topic]);
  const regionStories = useMemo(() => buildRegionStories(homeData.by_region), [homeData.by_region]);
  const watchlistStories = useMemo(() => sortStories(Array.isArray(homeData.watchlist) ? homeData.watchlist : []), [homeData.watchlist]);
  const briefingStats = useMemo(
    () =>
      buildBriefingStats({
        topCount: topStories.length,
        topicStoryCount: topicStories.length,
        regionStoryCount: regionStories.length,
        watchlistCount: watchlistStories.length,
      }),
    [topStories.length, topicStories.length, regionStories.length, watchlistStories.length],
  );

  const storiesByTab = useMemo(
    () => ({
      top: topStories,
      topic: topicStories,
      region: regionStories,
      watchlist: watchlistStories,
    }),
    [topStories, topicStories, regionStories, watchlistStories],
  );

  const tabMeta = {
    top: {
      title: 'Top Stories',
      subtitle: '',
      className: 'section-block-featured section-block-bare',
    },
    topic: {
      title: 'By Topic',
      subtitle: '',
      className: 'section-block-minimal',
    },
    region: {
      title: 'By Region',
      subtitle: '',
      className: 'section-block-minimal',
    },
    watchlist: {
      title: 'Watchlist',
      subtitle: '',
      className: 'section-block-watchlist',
    },
  };

  const activeStories = storiesByTab[activeTab] || [];
  const activeExpandedId = expandedByTab[activeTab];

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
          refreshError = requestError.message || 'Unable to refresh backend data.';
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

  const toggleStory = (tabKey, storyId) => {
    setExpandedByTab((current) => ({
      ...current,
      [tabKey]: current[tabKey] === storyId ? null : storyId,
    }));
  };

  useEffect(() => {
    loadHomeData();
  }, [debugEnabled]);

  useEffect(() => {
    setExpandedByTab((current) => {
      const next = { ...current };
      for (const tab of HOME_TABS) {
        const stories = storiesByTab[tab.key] || [];
        const firstId = stories[0]?.event_id || null;
        const existingId = next[tab.key];
        const stillExists = existingId && stories.some((story) => story.event_id === existingId);
        if (!stillExists) {
          next[tab.key] = firstId;
        }
      }
      return next;
    });
  }, [storiesByTab]);

  return (
    <div className="page-shell">
      <div className="page-backdrop" />
      <main className="page-content">
        <HeaderBar meta={homeData.meta} action={<RefreshButton loading={refreshing} onRefresh={() => loadHomeData({ isManualRefresh: true })} />} />

        {error ? <div className="status-banner">Latest refresh notice: {error}</div> : null}
        {loading ? <div className="status-banner">Loading latest homepage data...</div> : null}

        <section className="briefing-summary-card">
          <div className="briefing-summary-head">
            <h2>Today&apos;s Briefing</h2>
            <p>Key global developments in the past 24 hours.</p>
          </div>
          <div className="briefing-stat-grid">
            {briefingStats.map((stat) => (
              <article key={stat.key} className="briefing-stat">
                <div className="briefing-stat-value">
                  <span className={`briefing-stat-icon-badge briefing-stat-icon-badge-${stat.key}`}>
                    <span className="briefing-stat-icon" aria-hidden="true">
                      <BriefingStatIcon name={stat.icon} />
                    </span>
                  </span>
                  <strong>{stat.value}</strong>
                </div>
                <span>{stat.label}</span>
                <small>{stat.descriptor}</small>
              </article>
            ))}
          </div>
        </section>

        <nav className="home-tabs" aria-label="Homepage sections">
          {HOME_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              className={`home-tab ${activeTab === tab.key ? 'home-tab-active' : ''}`.trim()}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <SectionBlock
          title={tabMeta[activeTab].title}
          subtitle={tabMeta[activeTab].subtitle}
          className={tabMeta[activeTab].className}
          emptyMessage="No stories available in this section right now."
        >
          {activeStories.length > 0 ? (
            <div className={activeTab === 'top' ? 'top-tab-list' : 'tab-list'}>
              {activeStories.map((story, index) => (
                <StoryCard
                  key={`${activeTab}-${story.event_id}`}
                  story={story}
                  rank={index + 1}
                  isExpanded={activeExpandedId === story.event_id}
                  onToggle={(storyId) => toggleStory(activeTab, storyId)}
                  contextLabel={story._contextLabel || ''}
                  isHero={activeTab === 'top' && index === 0}
                />
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
