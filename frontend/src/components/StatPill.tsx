type StatPillProps = {
  label: string;
  value: string;
};

export function StatPill({ label, value }: StatPillProps) {
  return (
    <div className="stat-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
