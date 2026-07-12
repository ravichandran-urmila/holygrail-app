import { useAi } from "../lib/api";
import type { AiPanel } from "../lib/types";

const CARDS = [
  { key: "technical", icon: "🧠", title: "Technical", accent: "#a78bfa" },
  { key: "fundamental", icon: "📊", title: "Fundamental", accent: "#22d3ee" },
  { key: "narrative", icon: "📰", title: "Narrative", accent: "#ffb020" },
] as const;

function PanelCard({
  icon,
  title,
  accent,
  panel,
  loading,
}: {
  icon: string;
  title: string;
  accent: string;
  panel?: AiPanel;
  loading: boolean;
}) {
  return (
    <div
      className="card card-hover animate-fade-up flex flex-col p-5"
      style={{ background: `linear-gradient(160deg, ${accent}12, transparent 55%)` }}
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl text-base"
            style={{ background: `${accent}22`, boxShadow: `inset 0 0 0 1px ${accent}44` }}
          >
            {icon}
          </span>
          <span className="font-display text-[15px] font-bold" style={{ color: accent }}>
            {title}
          </span>
        </div>
        {panel && (
          <span className="chip !px-2 !py-0.5 text-[10px] text-faint">{panel.source}</span>
        )}
      </div>
      {loading ? (
        <div className="space-y-2.5">
          <div className="skeleton h-3 w-4/5" />
          <div className="skeleton h-3 w-full" />
          <div className="skeleton h-3 w-11/12" />
          <div className="skeleton h-3 w-3/4" />
          <div className="skeleton h-3 w-5/6" />
        </div>
      ) : (
        <div className="ai-prose" dangerouslySetInnerHTML={{ __html: panel?.html ?? "" }} />
      )}
    </div>
  );
}

export function AiPanels({ ticker, enabled }: { ticker: string; enabled: boolean }) {
  const { data, isLoading, isError } = useAi(ticker, enabled);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {CARDS.map((c) => (
        <PanelCard
          key={c.key}
          icon={c.icon}
          title={c.title}
          accent={c.accent}
          panel={
            isError
              ? { html: "<p>Analysis unavailable right now.</p>", source: "—" }
              : data?.[c.key]
          }
          loading={isLoading && !isError}
        />
      ))}
    </div>
  );
}
