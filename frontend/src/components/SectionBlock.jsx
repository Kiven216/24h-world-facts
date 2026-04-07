function SectionBlock({ title, subtitle, children, emptyMessage = 'No stories match the current filters.' }) {
  return (
    <section className="section-block">
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
