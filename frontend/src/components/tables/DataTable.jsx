// Plain DataTable on top of shadcn table primitives — sorting stays
// server-side (?ordering=), pagination is driven by the parent via props.
// Deliberately no client-side table library (see CRM_ANALYSIS_REPORT.md §15.4).

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function DataTableSkeleton({ rows = 5, cols = 5 }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {Array.from({ length: cols }).map((_, i) => (
            <TableHead key={i}>
              <Skeleton className="h-4 w-24" />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: rows }).map((_, r) => (
          <TableRow key={r}>
            {Array.from({ length: cols }).map((_, c) => (
              <TableCell key={c}>
                <Skeleton className="h-4 w-full" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/**
 * @param {Array<{key: string, header: string, className?: string, render?: (row) => ReactNode, sortable?: boolean}>} columns
 * @param {Array<object>} rows
 */
export default function DataTable({
  columns,
  rows,
  getRowId,
  isLoading = false,
  emptyState = null,
  sortValue = "",
  onSortChange,
  // pagination (server-side)
  page = 1,
  pageSize = 10,
  count = 0,
  onPageChange,
  onRowClick,
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const canSort = Boolean(onSortChange);

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.key} className={column.className}>
                  {column.sortable && canSort ? (
                    <button
                      type="button"
                      className="inline-flex items-center hover:text-foreground"
                      onClick={() =>
                        onSortChange(
                          sortValue === column.key ? `-${column.key}` : column.key,
                        )
                      }
                    >
                      {column.header}
                      {sortValue === column.key ? " ↑" : ""}
                      {sortValue === `-${column.key}` ? " ↓" : ""}
                    </button>
                  ) : (
                    column.header
                  )}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="p-0">
                  <DataTableSkeleton rows={pageSize > 5 ? 5 : pageSize} cols={columns.length} />
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length}>{emptyState}</TableCell>
              </TableRow>
            ) : (
              rows.filter(Boolean).map((row, idx) => (
                <TableRow
                  key={getRowId?.(row) ?? row?.id ?? idx}
                  className={onRowClick ? "cursor-pointer hover:bg-muted/50" : undefined}
                  onClick={(event) => {
                    if (!onRowClick || event.target.closest("a,button,input,select,textarea,[role='button']")) return;
                    onRowClick(row);
                  }}
                >
                  {columns.map((column) => (
                    <TableCell key={column.key} className={column.className}>
                      {column.render ? column.render(row) : row?.[column.key]}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {count > 0 ? (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {Math.min((page - 1) * pageSize + 1, count)}–{Math.min(page * pageSize, count)}{" "}
            of {count}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </Button>
            <span>
              Page {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
