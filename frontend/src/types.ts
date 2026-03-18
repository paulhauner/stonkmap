export type Holding = {
  exchange: string;
  ticker: string;
  units: string;
  is_index: boolean;
};

export type UnknownIndex = {
  portfolio_name: string;
  exchange: string;
  ticker: string;
  units: string;
};

export type CompanyExposure = {
  exchange: string | null;
  ticker: string;
  name: string;
  market_value: string;
  weight_percentage: string | null;
  latest_price: string | null;
  sector: string | null;
  country: string | null;
  currency: string | null;
  sources: string[];
};

export type Constituent = {
  ticker: string;
  exchange: string | null;
  source_ticker: string;
  source_exchange_code: string | null;
  name: string;
  asset_class: string | null;
  sector: string | null;
  country: string | null;
  currency: string | null;
  weight_percentage: string;
  units_held: string | null;
  market_value: string | null;
};

export type IndexBreakdown = {
  name: string;
  exchange: string;
  ticker: string;
  as_of: string;
  fetched_at: string | null;
  constituents: Constituent[];
};

export type PortfolioBreakdown = {
  name: string;
  holdings: Holding[];
  total_market_value: string;
  last_price_at: string | null;
  companies: CompanyExposure[];
  unknown_indexes: UnknownIndex[];
};

export type DashboardData = {
  generated_at: string;
  indexes: IndexBreakdown[];
  portfolios: PortfolioBreakdown[];
  unknown_indexes: UnknownIndex[];
  prices_last_updated_at: string | null;
};
