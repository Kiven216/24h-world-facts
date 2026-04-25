function SectionBlock({ title, subtitle, children, emptyMessage = 'No stories match the current filters.', className = '' }) {
  return (
    <section className={`section-block ${className}`.trim()}>
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      {children || <div className="empty-state">{emptyMessage}</div>}
    </section>
  );
}

export default SectionBlock;
