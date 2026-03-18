import { render, screen } from '@testing-library/react';

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
        onSelect={() => undefined}
      />,
    );

    expect(
      screen.getByText(
        'Price data is missing for this portfolio. Refresh prices to generate a meaningful heatmap.',
      ),
    ).toBeInTheDocument();
  });
});
