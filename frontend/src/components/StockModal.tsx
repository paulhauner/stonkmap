import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react';

import { formatMoney, formatPercent } from '../format';

type ModalStock = {
  exchange?: string | null;
  ticker: string;
  name: string;
  weightPercentage?: string | number | null;
  marketValue?: string | number | null;
  price?: string | number | null;
  sector?: string | null;
  country?: string | null;
  currency?: string | null;
  sources?: string[];
};

type StockModalProps = {
  stock: ModalStock | null;
  onClose: () => void;
};

export function StockModal({ stock, onClose }: StockModalProps) {
  return (
    <Dialog open={stock !== null} onClose={onClose} className="modal-root">
      <div className="modal-backdrop" aria-hidden="true" />
      <div className="modal-shell">
        <DialogPanel className="modal-panel">
          {stock ? (
            <>
              <DialogTitle as="h3" className="modal-title">
                {stock.ticker}
              </DialogTitle>
              <p className="modal-subtitle">{stock.name}</p>
              <div className="modal-grid">
                <div>
                  <span className="modal-label">Exchange</span>
                  <strong>{stock.exchange ?? 'Unknown'}</strong>
                </div>
                <div>
                  <span className="modal-label">Weight</span>
                  <strong>{formatPercent(stock.weightPercentage ?? null)}</strong>
                </div>
                <div>
                  <span className="modal-label">Market Value</span>
                  <strong>{formatMoney(stock.marketValue ?? null)}</strong>
                </div>
                <div>
                  <span className="modal-label">Latest Price</span>
                  <strong>{formatMoney(stock.price ?? null)}</strong>
                </div>
                <div>
                  <span className="modal-label">Sector</span>
                  <strong>{stock.sector ?? 'Unavailable'}</strong>
                </div>
                <div>
                  <span className="modal-label">Country</span>
                  <strong>{stock.country ?? 'Unavailable'}</strong>
                </div>
                <div>
                  <span className="modal-label">Currency</span>
                  <strong>{stock.currency ?? 'Unavailable'}</strong>
                </div>
              </div>
              {stock.sources && stock.sources.length > 0 ? (
                <div className="modal-sources">
                  <span className="modal-label">Sources</span>
                  <ul>
                    {stock.sources.map((source) => (
                      <li key={source}>{source}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : null}
        </DialogPanel>
      </div>
    </Dialog>
  );
}
