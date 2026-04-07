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

function StoryCard({ story, compact = false }) {
  const timeLabel = story.updated_at || story.published_at;
  // The UI intentionally keeps a 10-point display scale even though the raw field is named importance_score.
  const displayScore = Number(story.importance_score || 0).toFixed(1);

  return (
    <article className={`story-card ${compact ? 'story-card-compact' : ''}`}>
      <div className="story-card-topline">
        <span>{formatStatusLabel(story.status)}</span>
        <span>Score {displayScore}</span>
      </div>

      <h3>{story.headline}</h3>
      <p className="story-summary">{story.summary}</p>
      <p className="story-impact">{story.why_it_matters}</p>

      <div className="story-tags">
        <span>{story.region}</span>
        <span>{story.topic}</span>
      </div>

      <div className="story-footer">
        <span>{timeLabel}</span>
        <span>{story.source_list.join(' · ')}</span>
      </div>
    </article>
  );
}

export default StoryCard;
