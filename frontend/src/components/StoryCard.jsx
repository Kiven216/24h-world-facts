function formatStatusLabel(status) {
  const normalizedStatus = String(status || '').trim().toLowerCase();
  const labelMap = {
    official: 'Official',
    confirmed: 'Confirmed',
    'widely reported': 'Widely Reported',
    widely_reported: 'Widely Reported',
    developing: 'Developing',
    monitoring: 'Monitoring',
  };

  return labelMap[normalizedStatus] || status;
}

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

function StoryCard({ story, compact = false }) {
  const timeLabel = formatPublishedTime(story.published_at || story.updated_at);
  const articleUrl = String(story.article_url || '').trim();
  const isLinked = articleUrl.startsWith('http://') || articleUrl.startsWith('https://');
  // The UI intentionally keeps a 10-point display scale even though the raw field is named importance_score.
  const displayScore = Number(story.importance_score || 0).toFixed(1);
  const headlineNode = isLinked ? (
    <a
      className="story-card-link"
      href={articleUrl}
      target="_blank"
      rel="noreferrer"
      title={`Open original article from ${story.source_list.join(' / ') || 'source'}`}
    >
      {story.headline}
    </a>
  ) : (
    story.headline
  );

  return (
    <article className={`story-card ${compact ? 'story-card-compact' : ''}`}>
      <div className="story-card-topline">
        <span>{formatStatusLabel(story.status)}</span>
        <span>Score {displayScore}</span>
      </div>

      <h3>{headlineNode}</h3>
      <p className="story-summary">{story.summary}</p>
      {story.why_it_matters ? <p className="story-impact">{story.why_it_matters}</p> : null}

      <div className="story-tags">
        <span>{story.region}</span>
        <span>{story.topic}</span>
      </div>

      <div className="story-footer">
        <span>{timeLabel || 'Time unavailable'}</span>
        <span>{story.source_list.join(' · ')}</span>
      </div>
    </article>
  );
}

export default StoryCard;
