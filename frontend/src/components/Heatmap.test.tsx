import { fireEvent, render, screen } from '@testing-library/react';

import { Heatmap } from './Heatmap';

describe('Heatmap', () => {
  it('shows a clear message when all values are zero', () => {
    render(
      <Heatmap
        title="Portfolio heatmap"
        data={[
          {
            id: 'ASX:CBA',
            ticker: 'CBA',
            name: 'COMMONWEALTH BANK OF AUSTRALIA',
            size: 0,
            secondaryLabel: '$0.00',
          },
        ]}
        emptyMessage="Price data is missing for this portfolio. Refresh prices to generate a meaningful heatmap."
        valueLabel="value"
        onSelect={() => undefined}
      />,
    );

    expect(
      screen.getByText(
        'Price data is missing for this portfolio. Refresh prices to generate a meaningful heatmap.',
      ),
    ).toBeInTheDocument();
  });

  it('filters holdings by a minimum and maximum value range', () => {
    render(
      <Heatmap
        title="Portfolio heatmap"
        data={[
          {
            id: 'ASX:CBA',
            ticker: 'CBA',
            name: 'COMMONWEALTH BANK OF AUSTRALIA',
            size: 100,
            secondaryLabel: '$100.00',
          },
          {
            id: 'NASDAQ:MSFT',
            ticker: 'MSFT',
            name: 'Microsoft Corp',
            size: 1000,
            secondaryLabel: '$1,000.00',
          },
        ]}
        formatValue={(value) => `$${value.toFixed(2)}`}
        onSelect={() => undefined}
        valueLabel="value"
      />,
    );

    expect(screen.getByText('2 shown of 2 companies')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Hide below value'), {
      target: { value: '500' },
    });

    expect(screen.getByText('1 shown of 2 companies')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Hide above value'), {
      target: { value: '400' },
    });

    expect(screen.getByText('No holdings match the current value filter.')).toBeInTheDocument();
  });
});
