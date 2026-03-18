import { render, screen, waitFor } from '@testing-library/react';

import App from './App';

const dashboardPayload = {
  generated_at: '2026-03-18T09:00:00Z',
  prices_last_updated_at: '2026-03-18T09:10:00Z',
  indexes: [
    {
      name: 'Betashares Australia 200 ETF',
      exchange: 'ASX',
      ticker: 'A200',
      as_of: '2026-03-17',
      fetched_at: '2026-03-18T09:05:00Z',
      constituents: [
        {
          ticker: 'CBA',
          exchange: 'ASX',
          source_ticker: 'CBA AT',
          source_exchange_code: 'AT',
          name: 'COMMONWEALTH BANK OF AUSTRALIA',
          asset_class: 'Equities',
          sector: 'Financials',
          country: 'Australia',
          currency: 'AUD',
          weight_percentage: '9.12',
          units_held: '1000',
          market_value: '100000',
        },
      ],
    },
  ],
  portfolios: [
    {
      name: 'Core Portfolio',
      holdings: [
        {
          exchange: 'ASX',
          ticker: 'A200',
          units: '30',
        },
      ],
      total_market_value: '5000',
      last_price_at: '2026-03-18T09:10:00Z',
      companies: [
        {
          exchange: 'ASX',
          ticker: 'CBA',
          name: 'COMMONWEALTH BANK OF AUSTRALIA',
          market_value: '1200',
          weight_percentage: '24',
          latest_price: '137.5',
          sector: 'Financials',
          country: 'Australia',
          currency: 'AUD',
          sources: ['Index ASX:A200 (30 units)'],
        },
      ],
    },
  ],
};

describe('App', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders dashboard data from the API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => dashboardPayload,
      }),
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Core Portfolio')).toBeInTheDocument();
    });

    expect(screen.getByText('Index Breakdowns')).toBeInTheDocument();
    expect(screen.getByText('Betashares Australia 200 ETF')).toBeInTheDocument();
    expect(screen.getByText('Core Portfolio company exposure')).toBeInTheDocument();
  });
});
