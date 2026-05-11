import { useState } from 'react';

function formatPublishedTime(value) {
  const timestamp = Date.parse(value || '');
  if (!timestamp) {
    return '';
  }

  const diffHours = Math.max(0, (Date.now() - timestamp) / (1000 * 60 * 60));
  if (diffHours < 1) {
    return '<1h ago';
  }
  if (diffHours < 24) {
    return `${Math.floor(diffHours)}h ago`;
  }

  const articleDate = new Date(timestamp);
  return articleDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

function uniqueTags(tags) {
  const seen = new Set();
  const output = [];
  for (const tag of tags) {
    const normalized = String(tag || '').trim();
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    output.push(normalized);
  }
  return output;
}

function StoryCard({
  story,
  isExpanded = false,
  onToggle = null,
  rank = null,
  contextLabel = '',
  isHero = false,
}) {
  const [signalsOpen, setSignalsOpen] = useState(false);
  const articleUrl = String(story.article_url || '').trim();
  const isLinked = articleUrl.startsWith('http://') || articleUrl.startsWith('https://');
  const signalTags = Array.isArray(story.signal_tags) ? story.signal_tags : [];
  const sourceLabel = Array.isArray(story.source_list) ? story.source_list.join(' · ') : 'Unknown source';
  const timeLabel = formatPublishedTime(story.published_at || story.updated_at) || 'Time unavailable';
  const tags = uniqueTags([contextLabel, story.topic, story.region]);
  const displayTags = tags.slice(0, isExpanded ? 3 : 2);
  const scoreLabel = Number(story.importance_score || 0).toFixed(1);

  const onCardClick = () => {
    if (onToggle) {
      onToggle(story.event_id);
    }
  };

  const onCardKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onCardClick();
    }
  };

  const headlineNode = isLinked ? (
    <a
      className="story-card-link"
      href={articleUrl}
      target="_blank"
      rel="noreferrer"
      title={`Open original article from ${sourceLabel}`}
      onClick={(event) => event.stopPropagation()}
    >
      {story.headline}
    </a>
  ) : (
    story.headline
  );

  if (!isExpanded) {
    return (
      <article
        className={`story-card story-card-compact-row ${isHero ? 'story-card-hero-compact' : ''}`.trim()}
        onClick={onCardClick}
        onKeyDown={onCardKeyDown}
        role="button"
        tabIndex={0}
      >
        <div className="compact-rank">{rank || '-'}</div>
        <div className="compact-content">
          <h3>{headlineNode}</h3>
          <div className="story-context story-context-inline">
            {displayTags.map((tag) => (
              <span key={`${story.event_id}-${tag}`}>{tag}</span>
            ))}
          </div>
          <div className="story-footer">
            <span>{timeLabel}</span>
            <span>{sourceLabel}</span>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article
      className={`story-card ${isHero ? 'story-card-hero' : 'story-card-expanded'}`.trim()}
      onClick={onCardClick}
      onKeyDown={onCardKeyDown}
      role="button"
      tabIndex={0}
    >
      <div className="story-card-topline">
        <span className="story-badge">{isHero ? 'Top Story' : `Story #${rank || '-'}`}</span>
        <span className="story-meta-time">{timeLabel}</span>
      </div>

      <h3>{headlineNode}</h3>
      {story.summary ? <p className="story-summary">{story.summary}</p> : null}

      {story.why_it_matters ? (
        <div className="story-why-box">
          <span className="story-why-label">Why it matters</span>
          <p className="story-impact">{story.why_it_matters}</p>
        </div>
      ) : null}

      <div className="story-context">
        {displayTags.map((tag) => (
          <span key={`${story.event_id}-${tag}`}>{tag}</span>
        ))}
      </div>

      {signalTags.length > 0 ? (
        <div className="story-signals">
          <button
            type="button"
            className="story-signals-toggle"
            onClick={(event) => {
              event.stopPropagation();
              setSignalsOpen((current) => !current);
            }}
            aria-expanded={signalsOpen}
          >
            Signals · {signalTags.length}
          </button>
          {signalsOpen ? (
            <div className="story-signals-tags">
              {signalTags.map((tag) => (
                <span key={`${story.event_id}-${tag}`} className="story-signals-tag">
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="story-footer">
        <span className="story-meta-score">Score {scoreLabel}</span>
        <span className="story-meta-source">{sourceLabel}</span>
      </div>
    </article>
  );
}

export default StoryCard;
