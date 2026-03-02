"use client";

import { Fragment, useMemo, useState } from "react";
import { ArrowUpDown, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead } from "@/components/ui/table";
import { ScanIssue } from "@/types/scan";

function severityTone(severity: ScanIssue["severity"]) {
  if (severity === "P1") return "critical" as const;
  if (severity === "P2") return "warn" as const;
  return "info" as const;
}

function severityRank(severity: ScanIssue["severity"]) {
  if (severity === "P1") return 0;
  if (severity === "P2") return 1;
  if (severity === "P3") return 2;
  return 3;
}

function compareIssueId(a: string, b: string) {
  const getNum = (value: string) => {
    const match = value.match(/(\d+)/);
    return match ? Number.parseInt(match[1], 10) : Number.NaN;
  };
  const aNum = getNum(a);
  const bNum = getNum(b);
  if (!Number.isNaN(aNum) && !Number.isNaN(bNum) && aNum !== bNum) return aNum - bNum;
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

function normalize(value: string) {
  return value.toLowerCase().trim();
}

export function IssueTable({ issues }: { issues: ScanIssue[] }) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("All");
  const [category, setCategory] = useState("All");
  const [sortBy, setSortBy] = useState<"id" | "severity" | "category" | "title">("severity");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [expanded, setExpanded] = useState<string | null>(null);

  const onSort = (column: "id" | "severity" | "category" | "title") => {
    if (sortBy === column) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortBy(column);
    setSortDirection("asc");
  };

  const categories = useMemo(() => {
    const values = Array.from(new Set(issues.map((item) => item.category)));
    return values.sort((a, b) => a.localeCompare(b));
  }, [issues]);

  const filtered = useMemo(() => {
    const terms = normalize(query).split(/\s+/).filter(Boolean);
    const sorted = [...issues]
      .filter((item) => (severity === "All" ? true : item.severity === severity))
      .filter((item) => (category === "All" ? true : item.category === category))
      .filter((item) => {
        if (terms.length === 0) return true;
        const haystack = normalize([
          item.id,
          item.severity,
          item.title,
          item.category,
          item.description,
          item.severityJustification,
          ...item.stepsToReproduce
        ].join(" "));
        return terms.every((term) => haystack.includes(term));
      })
      .sort((a, b) => {
        let cmp = 0;
        if (sortBy === "severity") {
          cmp = severityRank(a.severity) - severityRank(b.severity);
          if (cmp === 0) cmp = compareIssueId(a.id, b.id);
        } else if (sortBy === "id") {
          cmp = compareIssueId(a.id, b.id);
        } else if (sortBy === "category") {
          cmp = a.category.localeCompare(b.category, undefined, { sensitivity: "base" });
          if (cmp === 0) cmp = compareIssueId(a.id, b.id);
        } else {
          cmp = a.title.localeCompare(b.title, undefined, { sensitivity: "base" });
          if (cmp === 0) cmp = compareIssueId(a.id, b.id);
        }
        return sortDirection === "asc" ? cmp : -cmp;
      });
    return sorted;
  }, [issues, severity, category, query, sortBy, sortDirection]);

  return (
    <Card className="border border-surface-border bg-surface-card p-4 shadow-none backdrop-blur-0">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-surface-muted" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search issues"
            className="border-surface-border bg-transparent pl-9 text-slate-900 placeholder:text-slate-500 outline-none ring-0 transition focus:border-slate-900 focus:shadow-none dark:focus:border-slate-200"
          />
        </div>
        <Select
          className="w-36 border-surface-border bg-transparent text-slate-900 outline-none ring-0 transition focus:border-slate-900 focus:shadow-none dark:focus:border-slate-200"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
        >
          <option>All</option>
          <option>P1</option>
          <option>P2</option>
          <option>P3</option>
          <option>Unknown</option>
        </Select>
        <Select
          className="w-52 border-surface-border bg-transparent text-slate-900 outline-none ring-0 transition focus:border-slate-900 focus:shadow-none dark:focus:border-slate-200"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option>All</option>
          {categories.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </Select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-surface-border bg-white">
        <Table>
          <THead className="bg-slate-50 text-slate-600">
            <tr>
              <TH className="text-slate-700">
                <button className="inline-flex items-center gap-1 font-semibold text-slate-700" type="button" onClick={() => onSort("id")}>
                  ID <ArrowUpDown className="h-3 w-3" />
                </button>
              </TH>
              <TH className="text-slate-700">
                <button className="inline-flex items-center gap-1 font-semibold text-slate-700" type="button" onClick={() => onSort("severity")}>
                  Severity <ArrowUpDown className="h-3 w-3" />
                </button>
              </TH>
              <TH className="text-slate-700">
                <button className="inline-flex items-center gap-1 font-semibold text-slate-700" type="button" onClick={() => onSort("category")}>
                  Category <ArrowUpDown className="h-3 w-3" />
                </button>
              </TH>
              <TH className="text-slate-700">
                <button className="inline-flex items-center gap-1 font-semibold text-slate-700" type="button" onClick={() => onSort("title")}>
                  Title <ArrowUpDown className="h-3 w-3" />
                </button>
              </TH>
            </tr>
          </THead>
          <TBody className="divide-y divide-slate-200">
            {filtered.length === 0 && (
              <tr>
                <TD colSpan={4} className="py-10 text-center text-slate-600">
                  No matching issues for current filters.
                </TD>
              </tr>
            )}

            {filtered.map((item) => (
              <Fragment key={item.id}>
                <tr className="cursor-pointer transition hover:bg-slate-50" onClick={() => setExpanded(expanded === item.id ? null : item.id)}>
                  <TD className="font-mono text-xs text-slate-700">{item.id}</TD>
                  <TD className="text-slate-800">
                    <Badge tone={severityTone(item.severity)}>{item.severity}</Badge>
                  </TD>
                  <TD className="capitalize text-slate-700">{item.category}</TD>
                  <TD className="font-medium text-slate-900">{item.title}</TD>
                </tr>

                {expanded === item.id && (
                  <tr>
                    <TD colSpan={4} className="bg-slate-50">
                      <div className="space-y-3 text-sm">
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Description</p>
                          <p className="mt-1 text-slate-700">{item.description || "Not provided"}</p>
                        </div>
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Severity Justification</p>
                          <p className="mt-1 text-slate-700">{item.severityJustification || "Not provided"}</p>
                        </div>
                        <div>
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">Steps To Reproduce</p>
                          {item.stepsToReproduce.length === 0 && <p className="mt-1 text-slate-600">Not provided</p>}
                          {item.stepsToReproduce.length > 0 && (
                            <ol className="mt-1 space-y-1 text-slate-700">
                              {item.stepsToReproduce.map((step, index) => (
                                <li key={`${item.id}-${index}`}>{step}</li>
                              ))}
                            </ol>
                          )}
                        </div>
                      </div>
                    </TD>
                  </tr>
                )}
              </Fragment>
            ))}
          </TBody>
        </Table>
      </div>
    </Card>
  );
}
