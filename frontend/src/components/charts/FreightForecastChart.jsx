import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

function FreightForecastChart({ forecast }) {
  if (!forecast) {
    return (
      <div className="forecast-empty">
        Forecast data unavailable
      </div>
    );
  }

  const predicted =
    forecast.predicted_30d_rate_usd ??
    forecast.predicted_rate ??
    0;

  const current =
    forecast.current_rate_usd ??
    forecast.current_rate ??
    0;

  const lower =
    forecast.forecast_range?.lower_usd ??
    forecast.prediction_interval?.lower ??
    predicted;

  const upper =
    forecast.forecast_range?.upper_usd ??
    forecast.prediction_interval?.upper ??
    predicted;

  const percentageChange =
    forecast.percentage_change ??
    0;

  const curve =
    forecast.forecast_curve?.length
      ? forecast.forecast_curve
      : [
          {
            day: 0,
            forecast: current,
            lower: current,
            upper: current,
          },
          {
            day: 30,
            forecast: predicted,
            lower,
            upper,
          },
        ];

  return (
    <div className="forecast-chart-card">
      <div className="forecast-chart-header">
        <div>
          <h3>Freight Forecast</h3>
          <p>
            AI 30-day freight projection with 90% prediction interval
          </p>
        </div>

        <div className="forecast-highlight">
          <span>30-Day Forecast</span>
          <strong>
            ${Number(predicted).toFixed(2)}/t
          </strong>
        </div>
      </div>

      <div className="forecast-chart">
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart
            data={curve}
            margin={{
              top: 10,
              right: 20,
              left: 10,
              bottom: 10,
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              opacity={0.15}
            />

            <XAxis
              dataKey="day"
              tickFormatter={(value) =>
                value === 0
                  ? "Today"
                  : `+${value}d`
              }
            />

            <YAxis
              tickFormatter={(value) =>
                `$${Number(value).toFixed(0)}`
              }
            />

            <Tooltip
              formatter={(value, name) => [
                `$${Number(value).toFixed(2)}/t`,
                name,
              ]}
              labelFormatter={(value) =>
                value === 0
                  ? "Today"
                  : `Day ${value}`
              }
            />

            <ReferenceLine
              x={0}
              strokeDasharray="5 5"
            />

            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fillOpacity={0.15}
              fill="#38bdf8"
            />

            <Area
              type="monotone"
              dataKey="lower"
              stroke="none"
              fillOpacity={0.15}
              fill="#38bdf8"
            />

            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#38bdf8"
              strokeWidth={3}
              dot={{ r: 5 }}
              activeDot={{ r: 7 }}
              name="AI Forecast"
            />

            <ReferenceLine
              y={current}
              strokeDasharray="5 5"
              label="Current"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="forecast-metrics">
        <div>
          <span>Current</span>
          <strong>
            ${Number(current).toFixed(2)}/t
          </strong>
        </div>

        <div>
          <span>Expected Change</span>
          <strong>
            {percentageChange >= 0 ? "+" : ""}
            {Number(percentageChange).toFixed(1)}%
          </strong>
        </div>

        <div>
          <span>90% Range</span>
          <strong>
            ${Number(lower).toFixed(2)} – $
            {Number(upper).toFixed(2)}
          </strong>
        </div>
      </div>
    </div>
  );
}

export default FreightForecastChart;