import { ChevronRight, Plus, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { type Topic } from '../api'

export function TopicList({
  topics,
  onSelect,
}: {
  topics: Topic[]
  onSelect: (topic: Topic) => void
}) {
  const [search, setSearch] = useState('')
  const [onlyRecurring, setOnlyRecurring] = useState(false)
  const [limit, setLimit] = useState(20)
  useEffect(() => setLimit(20), [search, onlyRecurring, topics])
  const filtered = topics.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) &&
      (!onlyRecurring || t.num_years >= 2),
  )
  return (
    <section className="topic-list">
      <div className="list-toolbar">
        <div className="search-field">
          <Search size={16} />
          <input
            aria-label="Search topics"
            placeholder="Find a topic"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <label className="check-label">
          <input
            type="checkbox"
            checked={onlyRecurring}
            onChange={(e) => setOnlyRecurring(e.target.checked)}
          />
          Recurring only
        </label>
      </div>
      {filtered.slice(0, limit).map((t) => (
        <button key={t.name} className="topic-row" onClick={() => onSelect(t)}>
          <span className="topic-copy">
            <strong>{t.name}</strong>
            <span>{t.summary}</span>
          </span>
          <span className="topic-years">
            {t.num_years ? (
              <>
                <span className="recurrence-label">
                  Seen in {t.num_years} exam{' '}
                  {t.num_years === 1 ? 'year' : 'years'}
                </span>
                <small>{t.years.join(' · ')}</small>
              </>
            ) : (
              <small>Teaching topic</small>
            )}
          </span>
          <ChevronRight size={17} />
        </button>
      ))}
      {!filtered.length && (
        <p className="p-6 muted">No topics match these filters.</p>
      )}
      {limit < filtered.length && (
        <div className="flex justify-center p-4">
          <button className="button quiet" onClick={() => setLimit(limit + 20)}>
            Show more topics ({filtered.length - limit} remaining)
            <Plus size={14} />
          </button>
        </div>
      )}
    </section>
  )
}
