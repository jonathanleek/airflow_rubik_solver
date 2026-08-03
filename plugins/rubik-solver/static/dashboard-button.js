function RubikSolverDashboardButton() {
  return React.createElement(
    'a',
    {
      href: 'rubik-solver/ui',
      style: {
        display: 'inline-block',
        margin: '0 0 16px',
        padding: '10px 14px',
        borderRadius: '8px',
        background: '#017cee',
        color: '#fff',
        fontWeight: 700,
        textDecoration: 'none',
      },
    },
    'Open Rubik Solver',
  );
}

globalThis['Rubik Solver Dashboard Button'] = RubikSolverDashboardButton;
globalThis.AirflowPlugin = RubikSolverDashboardButton;
