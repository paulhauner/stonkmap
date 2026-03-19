import { hierarchy, treemap, type HierarchyNode, type HierarchyRectangularNode } from 'd3-hierarchy';
import { useEffect, useRef, useState } from 'react';

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
  emptyMessage?: string;
  valueLabel: string;
  formatValue?: (value: number) => string;
};

type TooltipState = {
  x: number;
  y: number;
  item: HeatmapDatum;
} | null;

type HeatmapTreeNode = { children: HeatmapDatum[] } | HeatmapDatum;

function tileColor(value: number, maxValue: number) {
  const ratio = maxValue > 0 ? value / maxValue : 0;
  if (ratio > 0.72) return '#0f766e';
  if (ratio > 0.36) return '#155e75';
  if (ratio > 0.16) return '#1e293b';
  return '#334155';
}

function clipIdForTile(id: string) {
  return `heatmap-clip-${id.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
}

function formatWeightPercentage(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  return `${Number(value).toFixed(2)}% of portfolio`;
}

export function Heatmap({
  title,
  data,
  onSelect,
  emptyMessage,
  valueLabel,
  formatValue: providedFormatValue,
}: HeatmapProps) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 960, height: 340 });
  const [tooltip, setTooltip] = useState<TooltipState>(null);
  const [minimumVisibleValue, setMinimumVisibleValue] = useState(0);
  const [maximumVisibleValue, setMaximumVisibleValue] = useState(0);
  const maxValue = Math.max(...data.map((entry) => entry.size), 0);
  const formatValue =
    providedFormatValue ??
    ((value: number) =>
      new Intl.NumberFormat('en-AU', {
        maximumFractionDigits: 2,
      }).format(value));

  useEffect(() => {
    setMinimumVisibleValue(0);
    setMaximumVisibleValue(maxValue);
  }, [maxValue, data.length]);

  const filteredData = data.filter(
    (entry) => entry.size >= minimumVisibleValue && entry.size <= maximumVisibleValue,
  );
  const hasPositiveData = filteredData.some((entry) => entry.size > 0);
  const filterStep = maxValue > 0 ? Math.max(maxValue / 200, 0.01) : 0.01;

  useEffect(() => {
    const element = frameRef.current;
    if (!element) {
      return undefined;
    }

    const update = () => {
      setSize({
        width: element.clientWidth || 960,
        height: element.clientHeight || 340,
      });
    };

    update();

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', update);
      return () => window.removeEventListener('resize', update);
    }

    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const rootData = hierarchy<HeatmapTreeNode>({ children: filteredData })
    .sum((entry: HeatmapTreeNode) => ('size' in entry ? Math.max(entry.size, 0.01) : 0))
    .sort(
      (left: HierarchyNode<HeatmapTreeNode>, right: HierarchyNode<HeatmapTreeNode>) =>
        (right.value ?? 0) - (left.value ?? 0),
    );

  treemap<HeatmapTreeNode>()
    .size([size.width, size.height])
    .paddingInner(6)
    .round(true)(rootData);

  const leaves = rootData.leaves() as HierarchyRectangularNode<HeatmapDatum>[];

  return (
    <section className="heatmap-card">
      <div className="section-heading">
        <h3>{title}</h3>
        <span>
          {filteredData.length} shown of {data.length} companies
        </span>
      </div>
      <div className="heatmap-filters">
        <label className="heatmap-filter">
          <span>Hide below {formatValue(minimumVisibleValue)}</span>
          <input
            aria-label={`Hide below ${valueLabel}`}
            max={maximumVisibleValue}
            min={0}
            onChange={(event) => {
              const nextValue = Number(event.target.value);
              setMinimumVisibleValue(Math.min(nextValue, maximumVisibleValue));
            }}
            type="range"
            step={filterStep}
            value={minimumVisibleValue}
          />
        </label>
        <label className="heatmap-filter">
          <span>Hide above {formatValue(maximumVisibleValue)}</span>
          <input
            aria-label={`Hide above ${valueLabel}`}
            max={maxValue}
            min={minimumVisibleValue}
            onChange={(event) => {
              const nextValue = Number(event.target.value);
              setMaximumVisibleValue(Math.max(nextValue, minimumVisibleValue));
            }}
            type="range"
            step={filterStep}
            value={maximumVisibleValue}
          />
        </label>
      </div>
      <div className="heatmap-frame" ref={frameRef}>
        {filteredData.length > 0 && hasPositiveData ? (
          <>
            <svg
              aria-label={title}
              className="heatmap-svg"
              preserveAspectRatio="none"
              viewBox={`0 0 ${size.width} ${size.height}`}
            >
              {leaves.map((leaf: HierarchyRectangularNode<HeatmapDatum>) => {
                const item = leaf.data;
                const width = leaf.x1 - leaf.x0;
                const height = leaf.y1 - leaf.y0;
                const clipId = clipIdForTile(item.id);
                const inset = Math.max(2, Math.min(12, Math.min(width, height) * 0.14));
                const tickerFontSize = Math.max(
                  4,
                  Math.min(14, width * 0.22, height * 0.58),
                );
                const secondaryFontSize = Math.max(
                  4,
                  Math.min(11, width * 0.12, height * 0.26),
                );
                const showTicker = width > 8 && height > 8;
                const showSecondary = width > 72 && height > 34;

                return (
                  <g
                    className="heatmap-node"
                    key={item.id}
                    onClick={() => onSelect(item)}
                    onMouseLeave={() => setTooltip(null)}
                    onMouseMove={(event) => {
                      const bounds = frameRef.current?.getBoundingClientRect();
                      if (!bounds) {
                        return;
                      }
                      setTooltip({
                        x: event.clientX - bounds.left + 14,
                        y: event.clientY - bounds.top + 14,
                        item,
                      });
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        onSelect(item);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <title>{`${item.ticker}: ${item.name}`}</title>
                    <defs>
                      <clipPath id={clipId}>
                        <rect
                          height={Math.max(0, height - inset * 2)}
                          width={Math.max(0, width - inset * 2)}
                          x={leaf.x0 + inset}
                          y={leaf.y0 + inset}
                        />
                      </clipPath>
                    </defs>
                    <rect
                      fill={tileColor(item.size, maxValue)}
                      height={height}
                      rx={0}
                      stroke="#f8fafc"
                      strokeWidth={2}
                      width={width}
                      x={leaf.x0}
                      y={leaf.y0}
                    />
                    {showTicker ? (
                      <text
                        className="heatmap-label"
                        clipPath={`url(#${clipId})`}
                        style={{ fontSize: `${tickerFontSize}px` }}
                        x={leaf.x0 + inset}
                        y={leaf.y0 + inset + tickerFontSize}
                      >
                        {item.ticker}
                      </text>
                    ) : null}
                    {showSecondary ? (
                      <text
                        className="heatmap-secondary"
                        clipPath={`url(#${clipId})`}
                        style={{ fontSize: `${secondaryFontSize}px` }}
                        x={leaf.x0 + inset}
                        y={leaf.y0 + inset + tickerFontSize + secondaryFontSize + 6}
                      >
                        {item.secondaryLabel}
                      </text>
                    ) : null}
                  </g>
                );
              })}
            </svg>
            {tooltip ? (
              <div
                className="heatmap-tooltip"
                style={{
                  left: Math.min(tooltip.x, size.width - 220),
                  top: Math.min(tooltip.y, size.height - 88),
                }}
              >
                <strong>{tooltip.item.ticker}</strong>
                <span>{tooltip.item.name}</span>
                <span>{tooltip.item.secondaryLabel}</span>
                {formatWeightPercentage(tooltip.item.weightPercentage) ? (
                  <span>{formatWeightPercentage(tooltip.item.weightPercentage)}</span>
                ) : null}
              </div>
            ) : null}
          </>
        ) : (
          <div className="empty-state">
            {data.length === 0
              ? 'Refresh the backend data to populate this heatmap.'
              : filteredData.length === 0
                ? 'No holdings match the current value filter.'
              : emptyMessage ?? 'There is not enough weighted data to build this heatmap yet.'}
          </div>
        )}
      </div>
    </section>
  );
}
