import Button from './Button.jsx';

export default function Pagination({ page, pageSize, total, onPage }) {
  const pages = Math.max(1, Math.ceil((total || 0) / (pageSize || 1)));
  const canPrev = page > 1;
  const canNext = page < pages;

  const start = Math.max(1, page - 2);
  const end = Math.min(pages, page + 2);

  const nums = [];
  for (let p = start; p <= end; p += 1) nums.push(p);

  return (
    <div className="pagination">
      <Button variant="ghost" size="sm" disabled={!canPrev} onClick={() => onPage(page - 1)}>
        ←
      </Button>

      {start > 1 ? (
        <>
          <Button variant={page === 1 ? 'primary' : 'ghost'} size="sm" onClick={() => onPage(1)}>1</Button>
          <span className="pagination-dots">…</span>
        </>
      ) : null}

      {nums.map((p) => (
        <Button
          key={p}
          variant={page === p ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => onPage(p)}
        >
          {p}
        </Button>
      ))}

      {end < pages ? (
        <>
          <span className="pagination-dots">…</span>
          <Button variant={page === pages ? 'primary' : 'ghost'} size="sm" onClick={() => onPage(pages)}>
            {pages}
          </Button>
        </>
      ) : null}

      <Button variant="ghost" size="sm" disabled={!canNext} onClick={() => onPage(page + 1)}>
        →
      </Button>

      <div className="pagination-meta">
        {total ?? 0} всего
      </div>
    </div>
  );
}
