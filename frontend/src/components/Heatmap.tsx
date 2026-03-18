import { useMemo } from 'react';
import { ResponsiveContainer, Tooltip, Treemap } from 'recharts';

type HeatmapDatum = {
  id: string;
  ticker: string;
  name: string;
  size: number;
  secondaryLabel: string;
  exchange?: string | null;
  weightPercentage?: string | null;
  marketValue?: string | null;
  price?: string | null;
  sector?: string | null;
  country?: string | null;
  currency?: string | null;
  sources?: string[];
};

type HeatmapProps = {
  title: string;
  data: HeatmapDatum[];
  onSelect: (item: HeatmapDatum) => void;
};

type HeatmapNodeProps = {
  depth: number;
  x: number;
  y: number;
  width: number;
  height: number;
  payload?: HeatmapDatum;
  onSelect: (item: HeatmapDatum) => void;
};

function palette(value: number) {
  if (value > 7) return '#0f766e';
  if (value > 3) return '#0f766e';
  if (value > 1) return '#1f2937';
  return '#334155';
}

function HeatmapNode({ depth, x, y, width, height, payload, onSelect }: HeatmapNodeProps) {
  if (depth !== 1 || !payload) {
    return null;
  }

  const canFit = width > 48 && height > 36;

  return (
    <g
      onClick={() => onSelect(payload)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          onSelect(payload);
        }
      }}
      style={{ cursor: 'pointer' }}
    >
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={10}
        fill={palette(payload.size)}
        stroke="#f8fafc"
        strokeWidth={2}
      />
      {canFit ? (
        <>
          <text x={x + 10} y={y + 18} fill="#f8fafc" fontSize={14} fontWeight={700}>
            {payload.ticker}
          </text>
          <text x={x + 10} y={y + 35} fill="#cbd5e1" fontSize={11}>
            {payload.secondaryLabel}
          </text>
        </>
      ) : null}
    </g>
  );
}

export function Heatmap({ title, data, onSelect }: HeatmapProps) {
  const items = useMemo(
    () => data.map((entry) => ({ ...entry, value: Math.max(entry.size, 0.01) })),
    [data],
  );

  return (
    <section className="heatmap-card">
      <div className="section-heading">
        <h3>{title}</h3>
        <span>{data.length} companies</span>
      </div>
      <div className="heatmap-frame">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={items}
              dataKey="value"
              stroke="#f8fafc"
              content={(props) => <HeatmapNode {...props} onSelect={onSelect} />}
            >
              <Tooltip
                content={({ active, payload }) => {
                  const item = active ? (payload?.[0]?.payload as HeatmapDatum | undefined) : undefined;
                  if (!item) {
                    return null;
                  }
                  return (
                    <div className="heatmap-tooltip">
                      <strong>{item.ticker}</strong>
                      <span>{item.name}</span>
                      <span>{item.secondaryLabel}</span>
                    </div>
                  );
                }}
              />
            </Treemap>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">Refresh the backend data to populate this heatmap.</div>
        )}
      </div>
    </section>
  );
}
