import React, { useEffect, useState } from 'react';

import {
  Ship,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  ShieldAlert,
  Sliders,
  Activity,
  Clock,
  DollarSign,
  XCircle,
} from 'lucide-react';

import { evaluateDecision } from './services/api';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    cargo_qty: 75000,
    current_rate: 22.5,
    bunker_fuel: 620,
    congestion_days: 2.5,
    cargo_demand: 105,
    vessel_availability: 92,
    weather_index: 1.1,
    delivery_deadline_days: 30,
    origin: 'Australia (Port Hedland)',
    destination: 'Paradip',
    cargo_type: 'iron_ore',
    distance_nm: 3850,
  });

  const evaluateScenario = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await evaluateDecision(formData);
      setData(result);
    } catch (err) {
      console.error('Decision engine error:', err);

      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Unable to connect to the decision engine.';

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    evaluateScenario();
  }, []);

  const handleChange = (event) => {
    const { name, value } = event.target;

    const numericFields = [
      'cargo_qty',
      'current_rate',
      'bunker_fuel',
      'congestion_days',
      'cargo_demand',
      'vessel_availability',
      'weather_index',
      'delivery_deadline_days',
      'distance_nm',
    ];

    setFormData((previous) => ({
      ...previous,
      [name]: numericFields.includes(name)
        ? value === ''
          ? ''
          : Number(value)
        : value,
    }));
  };

  /*
   * Everything below is read from the backend response.
   * No local risk/decision/forecast formula is used.
   */

  const forecast = data?.forecast_module || {};
  const risk = data?.risk_module || {};
  const financial = data?.financial_summary || {};
  const scenario = data?.scenario_analysis || {};
  const charter = data?.charter_optimization_module || {};
  const port = data?.port_constraints_module || {};

  const recommendedAction =
    data?.recommended_action || 'WAIT';

  const riskLevel =
    risk?.risk_level || 'UNKNOWN';

  const riskScore =
    typeof risk?.risk_score === 'number'
      ? risk.risk_score
      : null;

  const currentRate =
    Number(
      forecast?.current_rate_usd_ton ??
      financial?.current_rate_usd_ton ??
      formData.current_rate
    );

  const forecastRate =
    Number(
      forecast?.predicted_rate_usd_ton ??
      forecast?.forecasted_30d_rate_usd ??
      financial?.forecast_rate_usd_ton ??
      currentRate
    );

  const rateChange =
    typeof forecast?.rate_change_pct === 'number'
      ? forecast.rate_change_pct
      : currentRate
        ? ((forecastRate - currentRate) / currentRate) * 100
        : 0;

  const bandLow =
    forecast?.prediction_interval_90?.low ??
    forecast?.band_low ??
    null;

  const bandHigh =
    forecast?.prediction_interval_90?.high ??
    forecast?.band_high ??
    null;

  const selectedVessel =
    charter?.selected_vessel ||
    charter?.recommended_vessel ||
    null;

  const vesselName =
    selectedVessel?.name ||
    charter?.recommended_vessel_name ||
    'No vessel selected';

  const vesselClass =
    selectedVessel?.vessel_class ||
    charter?.recommended_vessel_class ||
    '—';

  const vesselStatus =
    charter?.status ||
    'UNKNOWN';

  const totalVesselCost =
    charter?.total_cost_usd ??
    charter?.total_vessel_cost_usd ??
    null;

  const operationalDays =
    charter?.total_operational_days ??
    charter?.estimated_duration_days ??
    null;

  const formatNumber = (value, digits = 1) => {
    if (value === null || value === undefined || value === '') {
      return '—';
    }

    const number = Number(value);

    if (Number.isNaN(number)) {
      return '—';
    }

    return number.toLocaleString('en-IN', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  };

  const formatCurrency = (value, digits = 2) => {
    if (value === null || value === undefined || value === '') {
      return '—';
    }

    return Number(value).toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  };

  const getActionStyle = () => {
    switch (recommendedAction.toUpperCase()) {
      case 'CHARTERNOW':
      case 'CHARTER NOW':
        return {
          background: 'bg-emerald-950/30',
          border: 'border-emerald-500/50',
          text: 'text-emerald-400',
          icon: '🟢',
        };

      case 'WAIT':
        return {
          background: 'bg-red-950/20',
          border: 'border-red-500/50',
          text: 'text-red-400',
          icon: '🔴',
        };

      case 'WATCH':
      default:
        return {
          background: 'bg-amber-950/20',
          border: 'border-amber-500/50',
          text: 'text-amber-400',
          icon: '🟡',
        };
    }
  };

  const getRiskStyle = () => {
    switch (riskLevel.toUpperCase()) {
      case 'HIGH':
        return {
          text: 'text-red-400',
          background: 'bg-red-950/60',
          border: 'border-red-500/40',
        };

      case 'MEDIUM':
        return {
          text: 'text-amber-400',
          background: 'bg-amber-950/60',
          border: 'border-amber-500/40',
        };

      case 'LOW':
        return {
          text: 'text-emerald-400',
          background: 'bg-emerald-950/60',
          border: 'border-emerald-500/40',
        };

      default:
        return {
          text: 'text-slate-400',
          background: 'bg-slate-900',
          border: 'border-slate-700',
        };
    }
  };

  const actionStyle = getActionStyle();
  const riskStyle = getRiskStyle();

  return (
    <div className="min-h-screen bg-[#0b132b] text-slate-100 p-4 md:p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* HEADER */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <Ship className="w-8 h-8 text-blue-400" />

            <div>
              <h1 className="text-xl md:text-2xl font-bold tracking-wider text-white uppercase">
                Freight Intelligence Command Center
              </h1>

              <p className="text-xs text-slate-400">
                SIH 26006 • Inbound Overseas Import Decision Engine
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-xs bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-full text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>{loading ? 'ENGINE RUNNING' : 'SYSTEM ACTIVE'}</span>
          </div>
        </header>

        {/* WHAT-IF SIMULATOR */}
        <details
          className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden"
          open
        >
          <summary className="p-4 text-xs font-semibold uppercase tracking-wider text-slate-400 cursor-pointer flex justify-between items-center">
            <span className="flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-blue-400" />
              <span className="text-blue-400 font-bold">
                What-If Scenario Simulator
              </span>
            </span>

            <span className="text-blue-400 font-mono">
              Toggle Parameters
            </span>
          </summary>

          <div className="p-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-6 text-xs bg-slate-950/40">

            {/* Freight */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Freight Rate ($/t)</label>

                <input
                  type="number"
                  name="current_rate"
                  step="0.1"
                  value={formData.current_rate}
                  onChange={handleChange}
                  className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="current_rate"
                min="10"
                max="50"
                step="0.5"
                value={formData.current_rate || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Fuel */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Bunker Fuel ($/t)</label>

                <input
                  type="number"
                  name="bunker_fuel"
                  step="5"
                  value={formData.bunker_fuel}
                  onChange={handleChange}
                  className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="bunker_fuel"
                min="400"
                max="1000"
                step="10"
                value={formData.bunker_fuel || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Congestion */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Port Congestion (Days)</label>

                <input
                  type="number"
                  name="congestion_days"
                  step="0.5"
                  value={formData.congestion_days}
                  onChange={handleChange}
                  className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="congestion_days"
                min="0"
                max="10"
                step="0.5"
                value={formData.congestion_days || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Demand */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Cargo Demand Index</label>

                <input
                  type="number"
                  name="cargo_demand"
                  step="1"
                  value={formData.cargo_demand}
                  onChange={handleChange}
                  className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="cargo_demand"
                min="50"
                max="150"
                step="1"
                value={formData.cargo_demand || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Vessel Availability */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Vessel Availability Index</label>

                <input
                  type="number"
                  name="vessel_availability"
                  step="1"
                  value={formData.vessel_availability}
                  onChange={handleChange}
                  className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="vessel_availability"
                min="50"
                max="150"
                step="1"
                value={formData.vessel_availability || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Weather */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Weather Risk Index</label>

                <input
                  type="number"
                  name="weather_index"
                  step="0.1"
                  value={formData.weather_index}
                  onChange={handleChange}
                  className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="weather_index"
                min="0.5"
                max="3"
                step="0.1"
                value={formData.weather_index || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Deadline */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Delivery Deadline (Days)</label>

                <input
                  type="number"
                  name="delivery_deadline_days"
                  step="1"
                  value={formData.delivery_deadline_days}
                  onChange={handleChange}
                  className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="delivery_deadline_days"
                min="15"
                max="60"
                step="1"
                value={formData.delivery_deadline_days || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* Cargo */}
            <div className="space-y-2">
              <div className="flex justify-between text-slate-400">
                <label>Cargo Quantity (tons)</label>

                <input
                  type="number"
                  name="cargo_qty"
                  step="1000"
                  value={formData.cargo_qty}
                  onChange={handleChange}
                  className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-blue-400 font-mono font-bold"
                />
              </div>

              <input
                type="range"
                name="cargo_qty"
                min="25000"
                max="180000"
                step="5000"
                value={formData.cargo_qty || 0}
                onChange={handleChange}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            <div className="col-span-1 md:col-span-3 flex justify-between items-center pt-2">
              <span className="text-[11px] text-slate-400 italic">
                Change parameters and run the real decision engine.
              </span>

              <button
                onClick={evaluateScenario}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white font-semibold px-4 py-2 rounded transition-colors flex items-center space-x-2"
              >
                <Activity className="w-3.5 h-3.5" />

                <span>
                  {loading ? 'Running Engine...' : 'Run Simulation Engine'}
                </span>
              </button>
            </div>
          </div>
        </details>

        {/* ERROR */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl flex items-center space-x-3 text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />

            <div>
              <div className="font-semibold">
                Decision Engine Connection Failed
              </div>

              <div className="text-xs mt-1 text-red-300">
                {error}
              </div>
            </div>
          </div>
        )}

        {/* ROUTE OVERVIEW */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 grid grid-cols-1 md:grid-cols-4 gap-6 text-center">

          <div>
            <span className="text-xs uppercase font-semibold text-slate-400">
              Cargo
            </span>

            <div className="text-2xl font-extrabold text-white mt-1">
              {formatNumber(formData.cargo_qty, 0)} t
            </div>
          </div>

          <div>
            <span className="text-xs uppercase font-semibold text-slate-400">
              Route
            </span>

            <div className="flex justify-center items-center space-x-2 mt-2">
              <span className="font-bold text-slate-200">
                Australia
              </span>

              <ArrowRight className="w-4 h-4 text-blue-400" />

              <span className="font-bold text-slate-200">
                {formData.destination}
              </span>
            </div>
          </div>

          <div>
            <span className="text-xs uppercase font-semibold text-slate-400">
              Distance
            </span>

            <div className="text-2xl font-extrabold text-white mt-1">
              {formatNumber(formData.distance_nm, 0)} nm
            </div>
          </div>

          <div>
            <span className="text-xs uppercase font-semibold text-slate-400">
              Deadline
            </span>

            <div className="text-2xl font-extrabold text-white mt-1">
              {formatNumber(formData.delivery_deadline_days, 0)} days
            </div>
          </div>
        </div>

        {/* FORECAST */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">

          <div className="flex items-center space-x-2 text-xs uppercase font-semibold text-slate-400 tracking-wider">
            <TrendingUp className="w-4 h-4 text-blue-400" />
            <span>AI Freight Forecast</span>
          </div>

          <div className="flex flex-col md:flex-row items-center justify-between gap-6 py-6">

            <div className="text-center md:text-left">
              <span className="text-3xl md:text-4xl font-extrabold text-white">
                ${formatNumber(currentRate, 2)}/t
              </span>

              <span className="block text-xs text-slate-400 mt-1">
                Current Spot Rate
              </span>
            </div>

            <div className="flex-1 w-full text-center">
              <div className="border-t-2 border-dashed border-blue-500/40 relative">
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#0b132b] px-3 text-xs text-blue-400 font-medium border border-blue-500/30 rounded-full whitespace-nowrap">
                  {rateChange >= 0 ? '+' : ''}
                  {rateChange.toFixed(1)}% projected
                </span>
              </div>
            </div>

            <div className="text-center md:text-right">
              <span className="text-3xl md:text-4xl font-extrabold text-blue-400">
                ${formatNumber(forecastRate, 2)}/t
              </span>

              <span className="block text-xs text-slate-400 mt-1">
                30-Day AI Forecast
              </span>
            </div>
          </div>

          <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800 text-center md:text-left text-xs">
            <span className="text-slate-400 font-semibold">
              90% Prediction Band:{' '}
            </span>

            <span className="font-mono text-slate-200">
              {bandLow !== null && bandHigh !== null
                ? `$${formatNumber(bandLow, 2)} – $${formatNumber(bandHigh, 2)}/t`
                : 'Not available'}
            </span>

            {forecast?.model_mae !== undefined && (
              <span className="ml-4 text-slate-500">
                Model MAE: {formatNumber(forecast.model_mae, 2)}
              </span>
            )}
          </div>
        </div>

        {/* RISK + VESSEL */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* RISK */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">

            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h2 className="text-xs uppercase font-semibold text-slate-400 tracking-wider flex items-center space-x-2">
                <ShieldAlert className={`w-4 h-4 ${riskStyle.text}`} />
                <span>Route Risk Engine</span>
              </h2>

              <span
                className={`text-xs font-bold px-2 py-0.5 rounded border ${riskStyle.text} ${riskStyle.background} ${riskStyle.border}`}
              >
                {riskLevel} RISK
              </span>
            </div>

            <div className="flex justify-between items-center mt-5">

              <div>
                <span className={`text-4xl font-black ${riskStyle.text}`}>
                  {riskScore !== null ? riskScore.toFixed(1) : '—'}
                </span>

                <span className="text-xs text-slate-400 font-mono">
                  {' '} / 100
                </span>
              </div>

              <div className="text-right text-xs space-y-2 text-slate-300">
                <div>
                  Congestion:{' '}
                  <span className="font-semibold text-slate-100">
                    {formatNumber(risk?.sub_scores?.congestion, 1)}
                  </span>
                </div>

                <div>
                  Weather:{' '}
                  <span className="font-semibold text-slate-100">
                    {formatNumber(risk?.sub_scores?.weather, 1)}
                  </span>
                </div>

                <div>
                  Supply:{' '}
                  <span className="font-semibold text-slate-100">
                    {formatNumber(risk?.sub_scores?.supply_scarcity, 1)}
                  </span>
                </div>
              </div>
            </div>

            {risk?.key_drivers?.length > 0 && (
              <div className="mt-5 space-y-2">
                <span className="text-xs uppercase text-slate-500 font-semibold">
                  Key Drivers
                </span>

                {risk.key_drivers.map((driver, index) => (
                  <div
                    key={index}
                    className="text-xs text-slate-300 bg-slate-950/60 border border-slate-800 rounded p-2"
                  >
                    • {driver}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* VESSEL */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">

            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h2 className="text-xs uppercase font-semibold text-slate-400 tracking-wider flex items-center space-x-2">
                <Ship className="w-4 h-4 text-blue-400" />
                <span>Vessel Optimization</span>
              </h2>

              <span className="text-xs text-blue-400 font-semibold">
                {vesselStatus}
              </span>
            </div>

            <div className="mt-5">

              <div className="text-xs text-slate-400">
                Recommended Vessel
              </div>

              <div className="text-xl font-bold text-white mt-1">
                {vesselName}
              </div>

              <div className="text-sm text-blue-400 mt-1">
                {vesselClass}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-5">

              <div className="bg-slate-950/60 border border-slate-800 rounded p-3">
                <div className="text-xs text-slate-500">
                  Operational Time
                </div>

                <div className="text-lg font-bold text-white mt-1">
                  {operationalDays !== null
                    ? `${formatNumber(operationalDays, 1)} days`
                    : '—'}
                </div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 rounded p-3">
                <div className="text-xs text-slate-500">
                  Vessel Cost
                </div>

                <div className="text-lg font-bold text-white mt-1">
                  {totalVesselCost !== null
                    ? `$${formatCurrency(totalVesselCost, 0)}`
                    : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* PORT CONSTRAINTS */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">

          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <CheckCircle className="w-4 h-4 text-emerald-400" />

            <h2 className="text-xs uppercase font-semibold text-slate-400 tracking-wider">
              Port & Route Constraints
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-5">

            <div>
              <div className="text-xs text-slate-500">
                Origin
              </div>

              <div className="text-sm font-semibold text-white mt-1">
                {port?.origin || formData.origin}
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">
                Destination
              </div>

              <div className="text-sm font-semibold text-white mt-1">
                {port?.destination || formData.destination}
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">
                Cargo
              </div>

              <div className="text-sm font-semibold text-white mt-1">
                {port?.cargo_type || formData.cargo_type}
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500">
                Route Distance
              </div>

              <div className="text-sm font-semibold text-white mt-1">
                {formatNumber(port?.distance_nm ?? formData.distance_nm, 0)} nm
              </div>
            </div>
          </div>
        </div>

        {/* PRIMARY DECISION */}
        <div
          className={`border-2 rounded-xl p-6 ${actionStyle.background} ${actionStyle.border}`}
        >

          <div className="flex flex-col md:flex-row items-center justify-between gap-5">

            <div className="flex items-center space-x-3">
              <span className="text-3xl">
                {actionStyle.icon}
              </span>

              <div>
                <div className="text-xs uppercase text-slate-400 font-semibold">
                  AI Decision Engine
                </div>

                <h2 className={`text-3xl md:text-4xl font-black ${actionStyle.text}`}>
                  {recommendedAction}
                </h2>
              </div>
            </div>

            <div className="text-center md:text-right">

              <div className="text-sm text-slate-300">
                Vessel Class:{' '}
                <span className="font-bold text-white">
                  {vesselClass}
                </span>
              </div>

              <div className="text-sm text-slate-300 mt-1">
                Risk:{' '}
                <span className={`font-bold ${riskStyle.text}`}>
                  {riskLevel} ({riskScore !== null ? riskScore.toFixed(1) : '—'}/100)
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 border-t border-slate-800/80 pt-5">

            <h3 className="text-xs uppercase font-semibold text-slate-400 tracking-wider mb-3">
              Decision Reasoning
            </h3>

            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4 text-sm text-slate-300 leading-relaxed">
              {data?.reasoning || 'No reasoning returned by the decision engine.'}
            </div>
          </div>
        </div>

        {/* FINANCIAL SCENARIOS */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">

          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <DollarSign className="w-4 h-4 text-blue-400" />

            <h2 className="text-xs uppercase font-semibold text-slate-400 tracking-wider">
              Financial Scenario Analysis
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">

            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4">
              <div className="text-xs text-slate-500">
                Book Now
              </div>

              <div className="text-2xl font-bold text-white mt-1">
                ₹{formatNumber(scenario?.scenario_book_now_inr_cr, 2)} Cr
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4">
              <div className="text-xs text-slate-500">
                Wait 30 Days
              </div>

              <div className="text-2xl font-bold text-white mt-1">
                ₹{formatNumber(scenario?.scenario_wait_30d_inr_cr, 2)} Cr
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4">
              <div className="text-xs text-slate-500">
                Exposure Delta
              </div>

              <div className="text-2xl font-bold text-blue-400 mt-1">
                ₹{formatNumber(scenario?.exposure_delta_inr_cr, 2)} Cr
              </div>
            </div>
          </div>

          {scenario?.basis && (
            <div className="text-xs text-slate-500 mt-4">
              Basis: {scenario.basis}
            </div>
          )}
        </div>

        {/* ENGINE STATUS */}
        <div className="flex flex-wrap gap-3 text-xs text-slate-400">

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded px-3 py-2">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
            ML Forecast
          </div>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded px-3 py-2">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
            Risk Engine
          </div>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded px-3 py-2">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
            Port Constraints
          </div>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded px-3 py-2">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
            OR-Tools Vessel Optimization
          </div>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded px-3 py-2">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            Live Decision Evaluation
          </div>
        </div>

      </div>
    </div>
  );
}