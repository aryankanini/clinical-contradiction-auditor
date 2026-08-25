import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { endpoints } from "../api/endpoints";
import type { Role } from "../api/types";
import { useRole } from "../hooks/useRole";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/batches", label: "Batches" },
  { to: "/findings", label: "Findings" },
  { to: "/queues", label: "Queues" },
  { to: "/rule-packs", label: "Rule packs" },
  { to: "/compliance", label: "Compliance" },
];

const ROLES: Role[] = ["steward", "analyst", "compliance"];

function RoleSwitcher() {
  const { role, userId, setRole, setUserId } = useRole();

  return (
    <div className="flex items-center gap-2">
      <input
        aria-label="User id"
        value={userId}
        onChange={(event) => setUserId(event.target.value)}
        className="w-40 rounded-md border border-[var(--color-line)] px-2 py-1 text-sm"
      />
      <select
        aria-label="Role"
        value={role}
        onChange={(event) => setRole(event.target.value as Role)}
        className="rounded-md border border-[var(--color-line)] bg-white px-2 py-1 text-sm capitalize"
      >
        {ROLES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}

/**
 * FR-011 requires the audit-only boundary be visible, not buried in a tooltip.
 * The banner is part of the shell so it cannot be lost on any screen.
 */
function AuditOnlyBanner() {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: endpoints.health,
  });

  const statusBadges: string[] = [];
  if (data?.audit_engine_is_placeholder) {
    statusBadges.push("Placeholder rule engine — module 2 pending");
  }
  if (data && !data.ai_enabled) {
    statusBadges.push("AI explanation disabled");
  }

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-xs text-amber-900">
      <strong className="font-semibold">Audit-only.</strong> This system does
      not diagnose, prescribe, or alter clinical intent. Deterministic rules
      establish findings; AI provides explanation and confidence context only.
      {statusBadges.length > 0 && (
        <>
          {" "}
          {statusBadges.map((badge, index) => (
            <span
              key={badge}
              className="mr-2 inline-block rounded bg-amber-200 px-1.5 py-0.5 font-medium text-amber-900 last:mr-0"
            >
              {index > 0 && " "}
              {badge}
            </span>
          ))}
        </>
      )}
    </div>
  );
}

export function AppShell() {
  return (
    <div className="flex min-h-full flex-col">
      <AuditOnlyBanner />
      <header className="flex items-center justify-between gap-6 border-b border-[var(--color-line)] bg-[var(--color-surface)] px-6 py-3">
        <div>
          <h1 className="text-base font-semibold">
            Clinical Data Integrity Auditor
          </h1>
          <p className="text-xs text-[var(--color-muted)]">
            Cross-resource consistency auditing for FHIR patient records
          </p>
        </div>
        <RoleSwitcher />
      </header>

      <div className="flex flex-1">
        <nav className="w-48 shrink-0 border-r border-[var(--color-line)] bg-[var(--color-surface)] p-3">
          <ul className="space-y-1">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `block rounded-md px-3 py-2 text-sm ${
                      isActive
                        ? "bg-slate-900 text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
