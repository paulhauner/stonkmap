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

export function Heatmap({ title, data, onSelect, emptyMessage }: HeatmapProps) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 960, height: 340 });
  const [tooltip, setTooltip] = useState<TooltipState>(null);
  const hasPositiveData = data.some((entry) => entry.size > 0);

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

  const root = hierarchy<HeatmapTreeNode>({ children: data })
    .sum((entry: HeatmapTreeNode) => ('size' in entry ? Math.max(entry.size, 0.01) : 0))
    .sort(
      (left: HierarchyNode<HeatmapTreeNode>, right: HierarchyNode<HeatmapTreeNode>) =>
        (right.value ?? 0) - (left.value ?? 0),
    );

  treemap<HeatmapTreeNode>()
    .size([size.width, size.height])
    .paddingInner(6)
    .round(true)(root);

  const leaves = root.leaves() as HierarchyRectangularNode<HeatmapDatum>[];
  const maxValue = Math.max(...data.map((entry) => entry.size), 0);

  return (
    <section className="heatmap-card">
      <div className="section-heading">
        <h3>{title}</h3>
        <span>{data.length} companies</span>
      </div>
      <div className="heatmap-frame" ref={frameRef}>
        {data.length > 0 && hasPositiveData ? (
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
                const showTicker = width > 70 && height > 32;
                const showSecondary = width > 110 && height > 62;

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
                      <text className="heatmap-label" x={leaf.x0 + 12} y={leaf.y0 + 22}>
                        {item.ticker}
                      </text>
                    ) : null}
                    {showSecondary ? (
                      <text className="heatmap-secondary" x={leaf.x0 + 12} y={leaf.y0 + 42}>
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
              </div>
            ) : null}
          </>
        ) : (
          <div className="empty-state">
            {data.length === 0
              ? 'Refresh the backend data to populate this heatmap.'
              : emptyMessage ?? 'There is not enough weighted data to build this heatmap yet.'}
          </div>
        )}
      </div>
    </section>
  );
}
