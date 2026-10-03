"use client";

/**
 * Compliance & Monitoring Dashboard (Phase 7, Fragments 94 & 101).
 * 
 * Provides an industry user with:
 * - Compliance health score gauge
 * - Category-wise compliance breakdown
 * - Active alerts with severity indicators
 * - Prioritized action queue with urgency scores
 * - Upcoming and overdue deadline timeline
 */

import { useEffect, useState, useCallback } from "react";
import {
  ComplianceDashboardMetrics,
  ComplianceAlert,
  CompliancePrioritizedItem,
  ComplianceStatusResponse,
  fetchComplianceDashboard,
  fetchComplianceAlerts,
  fetchCompliancePriorities,
  fetchComplianceStatus,
  PRIORITY_COLORS,
  STATUS_COLORS,
  CATEGORY_LABELS,
  CATEGORY_ICONS,
  CompliancePriority,
  ComplianceRecordStatus,
  ComplianceCategory,
} from "@/lib/compliance";

// ---------------------------------------------------------------------------
// Health Gauge Component
// ---------------------------------------------------------------------------

function HealthGauge({ rate, health }: { rate: number; health: string }) {
  const color =
    health === "HEALTHY"
      ? "#16a34a"
      : health === "AT_RISK"
      ? "#f59e0b"
      : "#dc2626";
  const label =
    health === "HEALTHY"
      ? "Healthy"
      : health === "AT_RISK"
      ? "At Risk"
      : "Non-Compliant";

  return (
    <div
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        borderRadius: "16px",
        padding: "24px",
        textAlign: "center",
        border: `2px solid ${color}40`,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "4px",
          background: `linear-gradient(90deg, ${color}, ${color}80)`,
        }}
      />
      <div
        style={{
          fontSize: "56px",
          fontWeight: 800,
          color,
          lineHeight: 1,
          marginBottom: "8px",
        }}
      >
        {rate.toFixed(0)}%
      </div>
      <div
        style={{
          fontSize: "14px",
          fontWeight: 600,
          color: `${color}cc`,
          textTransform: "uppercase",
          letterSpacing: "1px",
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
        Compliance Rate
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metric Card
// ---------------------------------------------------------------------------

function MetricCard({
  label,
  value,
  color,
  icon,
}: {
  label: string;
  value: number | string;
  color: string;
  icon: string;
}) {
  return (
    <div
      style={{
        background: `linear-gradient(135deg, ${color}10 0%, ${color}05 100%)`,
        borderRadius: "12px",
        padding: "16px",
        border: `1px solid ${color}30`,
        display: "flex",
        alignItems: "center",
        gap: "12px",
      }}
    >
      <span style={{ fontSize: "24px" }}>{icon}</span>
      <div>
        <div style={{ fontSize: "24px", fontWeight: 700, color }}>
          {value}
        </div>
        <div style={{ fontSize: "12px", color: "#94a3b8" }}>{label}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alert Card
// ---------------------------------------------------------------------------

function AlertCard({ alert }: { alert: ComplianceAlert }) {
  const borderColor = PRIORITY_COLORS[alert.priority] || "#6b7280";
  const typeEmoji =
    alert.alert_type === "OVERDUE"
      ? "🔴"
      : alert.alert_type === "EXPIRING"
      ? "⚫"
      : alert.alert_type === "DUE_SOON"
      ? "🟡"
      : "🟠";

  return (
    <div
      style={{
        background: "#0f172a",
        borderRadius: "10px",
        padding: "14px 16px",
        borderLeft: `4px solid ${borderColor}`,
        marginBottom: "8px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "6px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span>{typeEmoji}</span>
          <span style={{ fontWeight: 600, color: "#e2e8f0", fontSize: "13px" }}>
            {alert.requirement_title}
          </span>
        </div>
        <span
          style={{
            fontSize: "11px",
            padding: "2px 8px",
            borderRadius: "6px",
            background: `${borderColor}20`,
            color: borderColor,
            fontWeight: 600,
          }}
        >
          {alert.priority}
        </span>
      </div>
      <div style={{ fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
        {alert.message}
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: "8px",
          fontSize: "11px",
          color: "#64748b",
        }}
      >
        <span>
          {CATEGORY_ICONS[alert.category]} {CATEGORY_LABELS[alert.category]}
        </span>
        <span>
          Penalty: ₹{alert.penalty_exposure.toLocaleString("en-IN")}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Priority Queue Item
// ---------------------------------------------------------------------------

function PriorityItem({ item }: { item: CompliancePrioritizedItem }) {
  const statusColor = STATUS_COLORS[item.status] || "#6b7280";
  const priorityColor = PRIORITY_COLORS[item.priority] || "#6b7280";

  return (
    <div
      style={{
        background: "#0f172a",
        borderRadius: "10px",
        padding: "14px 16px",
        marginBottom: "8px",
        display: "flex",
        gap: "12px",
        alignItems: "flex-start",
      }}
    >
      <div
        style={{
          width: "32px",
          height: "32px",
          borderRadius: "50%",
          background: `${priorityColor}20`,
          color: priorityColor,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 800,
          fontSize: "14px",
          flexShrink: 0,
        }}
      >
        #{item.rank}
      </div>
      <div style={{ flex: 1 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "4px",
          }}
        >
          <span
            style={{ fontWeight: 600, color: "#e2e8f0", fontSize: "13px" }}
          >
            {item.requirement_title}
          </span>
          <span
            style={{
              fontSize: "11px",
              padding: "2px 8px",
              borderRadius: "6px",
              background: `${statusColor}20`,
              color: statusColor,
              fontWeight: 600,
            }}
          >
            {item.status.replace(/_/g, " ")}
          </span>
        </div>
        <div style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "6px" }}>
          {item.recommended_action}
        </div>
        <div
          style={{
            display: "flex",
            gap: "16px",
            fontSize: "11px",
            color: "#64748b",
          }}
        >
          <span>
            📅 Due: {item.due_date}
          </span>
          <span style={{ color: item.days_remaining < 0 ? "#dc2626" : "#94a3b8" }}>
            {item.days_remaining < 0
              ? `${Math.abs(item.days_remaining)}d overdue`
              : `${item.days_remaining}d remaining`}
          </span>
          <span>Score: {item.urgency_score.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Category Breakdown Card
// ---------------------------------------------------------------------------

function CategoryCard({
  category,
  total,
  compliant,
  due_soon,
  overdue,
  expired,
  compliance_rate_percent,
}: {
  category: ComplianceCategory;
  total: number;
  compliant: number;
  due_soon: number;
  overdue: number;
  expired: number;
  compliance_rate_percent: number;
}) {
  const barWidth = Math.max(compliance_rate_percent, 5);
  const barColor =
    compliance_rate_percent >= 80
      ? "#16a34a"
      : compliance_rate_percent >= 50
      ? "#f59e0b"
      : "#dc2626";

  return (
    <div
      style={{
        background: "#0f172a",
        borderRadius: "10px",
        padding: "14px 16px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "18px" }}>{CATEGORY_ICONS[category]}</span>
          <span style={{ fontWeight: 600, color: "#e2e8f0", fontSize: "13px" }}>
            {CATEGORY_LABELS[category]}
          </span>
        </div>
        <span style={{ fontWeight: 700, color: barColor, fontSize: "14px" }}>
          {compliance_rate_percent.toFixed(0)}%
        </span>
      </div>
      <div
        style={{
          width: "100%",
          height: "6px",
          borderRadius: "3px",
          background: "#1e293b",
          marginBottom: "8px",
        }}
      >
        <div
          style={{
            width: `${barWidth}%`,
            height: "100%",
            borderRadius: "3px",
            background: `linear-gradient(90deg, ${barColor}, ${barColor}99)`,
            transition: "width 0.5s ease",
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          gap: "12px",
          fontSize: "11px",
          color: "#94a3b8",
        }}
      >
        <span>✅ {compliant}</span>
        <span style={{ color: "#f59e0b" }}>⏰ {due_soon}</span>
        <span style={{ color: "#dc2626" }}>⚠️ {overdue}</span>
        {expired > 0 && <span style={{ color: "#991b1b" }}>💀 {expired}</span>}
        <span style={{ marginLeft: "auto" }}>Total: {total}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Compliance Dashboard Page
// ---------------------------------------------------------------------------

export default function ComplianceDashboardPage() {
  const [metrics, setMetrics] = useState<ComplianceDashboardMetrics | null>(null);
  const [alerts, setAlerts] = useState<ComplianceAlert[]>([]);
  const [alertCounts, setAlertCounts] = useState({ critical: 0, high: 0 });
  const [priorities, setPriorities] = useState<CompliancePrioritizedItem[]>([]);
  const [status, setStatus] = useState<ComplianceStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // For demo purposes, use a hardcoded business ID
  // In production, this would come from auth context
  const businessId = "demo-business-id";

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardData, alertsData, prioritiesData, statusData] =
        await Promise.allSettled([
          fetchComplianceDashboard(businessId),
          fetchComplianceAlerts(businessId),
          fetchCompliancePriorities(businessId),
          fetchComplianceStatus(businessId),
        ]);

      if (dashboardData.status === "fulfilled") {
        setMetrics(dashboardData.value);
      }
      if (alertsData.status === "fulfilled") {
        setAlerts(alertsData.value.items);
        setAlertCounts({
          critical: alertsData.value.critical_count,
          high: alertsData.value.high_count,
        });
      }
      if (prioritiesData.status === "fulfilled") {
        setPriorities(prioritiesData.value.items);
      }
      if (statusData.status === "fulfilled") {
        setStatus(statusData.value);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load compliance data");
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#030712",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#94a3b8",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "32px", marginBottom: "12px" }}>⏳</div>
          <div>Loading compliance data...</div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#030712",
        color: "#e2e8f0",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
          borderBottom: "1px solid #1e293b",
          padding: "24px 32px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h1
              style={{
                fontSize: "24px",
                fontWeight: 800,
                margin: 0,
                background: "linear-gradient(135deg, #60a5fa, #a78bfa)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              🛡️ Compliance & Monitoring
            </h1>
            <p style={{ fontSize: "13px", color: "#94a3b8", margin: "4px 0 0" }}>
              Track statutory obligations, renewals, and filing deadlines
            </p>
          </div>
          {alertCounts.critical > 0 && (
            <div
              style={{
                background: "#dc262620",
                border: "1px solid #dc262640",
                borderRadius: "10px",
                padding: "8px 16px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span style={{ fontSize: "16px" }}>🚨</span>
              <span style={{ color: "#dc2626", fontWeight: 700, fontSize: "14px" }}>
                {alertCounts.critical} Critical
              </span>
              {alertCounts.high > 0 && (
                <span style={{ color: "#ea580c", fontWeight: 600, fontSize: "13px" }}>
                  · {alertCounts.high} High
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {error && (
        <div
          style={{
            margin: "16px 32px",
            padding: "12px 16px",
            background: "#dc262620",
            border: "1px solid #dc262640",
            borderRadius: "8px",
            color: "#fca5a5",
            fontSize: "13px",
          }}
        >
          ⚠️ {error}
        </div>
      )}

      <div style={{ padding: "24px 32px" }}>
        {/* Top Row: Health Gauge + Metrics */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 3fr",
            gap: "20px",
            marginBottom: "24px",
          }}
        >
          {/* Health Gauge */}
          <HealthGauge
            rate={metrics?.compliance_rate_percent ?? status?.overall_compliance_rate ?? 100}
            health={status?.overall_health ?? "HEALTHY"}
          />

          {/* Metric Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "12px",
            }}
          >
            <MetricCard
              label="Total Obligations"
              value={metrics?.total_obligations ?? 0}
              color="#3b82f6"
              icon="📋"
            />
            <MetricCard
              label="Compliant"
              value={metrics?.compliant_count ?? 0}
              color="#16a34a"
              icon="✅"
            />
            <MetricCard
              label="Due Soon"
              value={metrics?.due_soon_count ?? 0}
              color="#f59e0b"
              icon="⏰"
            />
            <MetricCard
              label="Overdue"
              value={metrics?.overdue_count ?? 0}
              color="#dc2626"
              icon="🔴"
            />
            <MetricCard
              label="In Progress"
              value={metrics?.in_progress_count ?? 0}
              color="#8b5cf6"
              icon="🔄"
            />
            <MetricCard
              label="Submitted"
              value={metrics?.submitted_count ?? 0}
              color="#06b6d4"
              icon="📤"
            />
            <MetricCard
              label="Penalty Exposure"
              value={`₹${(metrics?.total_penalty_exposure ?? 0).toLocaleString("en-IN")}`}
              color="#ef4444"
              icon="💰"
            />
            <MetricCard
              label="Next Deadline"
              value={metrics?.next_deadline ?? "N/A"}
              color="#94a3b8"
              icon="📅"
            />
          </div>
        </div>

        {/* Middle Row: Category Breakdown + Alerts */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "20px",
            marginBottom: "24px",
          }}
        >
          {/* Category Breakdown */}
          <div
            style={{
              background: "#1e293b",
              borderRadius: "14px",
              padding: "20px",
            }}
          >
            <h2
              style={{
                fontSize: "16px",
                fontWeight: 700,
                margin: "0 0 16px",
                color: "#e2e8f0",
              }}
            >
              📊 Category Breakdown
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {status?.category_breakdown?.length ? (
                status.category_breakdown.map((cat) => (
                  <CategoryCard key={cat.category} {...cat} />
                ))
              ) : (
                <div style={{ color: "#64748b", fontSize: "13px", padding: "20px", textAlign: "center" }}>
                  No compliance data available. Generate compliance records to see category breakdown.
                </div>
              )}
            </div>
          </div>

          {/* Alerts */}
          <div
            style={{
              background: "#1e293b",
              borderRadius: "14px",
              padding: "20px",
            }}
          >
            <h2
              style={{
                fontSize: "16px",
                fontWeight: 700,
                margin: "0 0 16px",
                color: "#e2e8f0",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              🔔 Active Alerts
              {alerts.length > 0 && (
                <span
                  style={{
                    fontSize: "11px",
                    background: "#dc262630",
                    color: "#fca5a5",
                    padding: "2px 8px",
                    borderRadius: "10px",
                    fontWeight: 600,
                  }}
                >
                  {alerts.length}
                </span>
              )}
            </h2>
            <div
              style={{
                maxHeight: "400px",
                overflowY: "auto",
              }}
            >
              {alerts.length > 0 ? (
                alerts.map((alert) => <AlertCard key={alert.id} alert={alert} />)
              ) : (
                <div style={{ color: "#64748b", fontSize: "13px", padding: "20px", textAlign: "center" }}>
                  ✅ No active alerts. All compliance obligations are on track.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Row: Prioritized Action Queue */}
        <div
          style={{
            background: "#1e293b",
            borderRadius: "14px",
            padding: "20px",
          }}
        >
          <h2
            style={{
              fontSize: "16px",
              fontWeight: 700,
              margin: "0 0 16px",
              color: "#e2e8f0",
            }}
          >
            🎯 Prioritized Action Queue
          </h2>
          <div>
            {priorities.length > 0 ? (
              priorities.map((item) => (
                <PriorityItem key={item.record_id} item={item} />
              ))
            ) : (
              <div style={{ color: "#64748b", fontSize: "13px", padding: "20px", textAlign: "center" }}>
                No pending compliance actions. All obligations are fulfilled.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
