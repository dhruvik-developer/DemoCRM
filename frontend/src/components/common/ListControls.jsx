import { ArrowUpDown, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuRadioGroup,
  DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function ListControls({ filterValue = "all", filterOptions = [], onFilterChange, sortValue = "", sortOptions = [], onSortChange, pinnedOnly = false, onPinnedOnlyChange }) {
  return (
    <div className="flex items-center divide-x rounded-lg border bg-background">
      <DropdownMenu>
        <DropdownMenuTrigger asChild><Button variant="ghost" size="sm" className="rounded-r-none"><Filter /> Filter{filterValue !== "all" || pinnedOnly ? <span className="size-1.5 rounded-full bg-primary" /> : null}</Button></DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel>Show records</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={filterValue} onValueChange={onFilterChange}>
            {filterOptions.map((option) => <DropdownMenuRadioItem key={option.value} value={option.value}>{option.label}</DropdownMenuRadioItem>)}
          </DropdownMenuRadioGroup>
          <DropdownMenuSeparator />
          <DropdownMenuRadioGroup value={pinnedOnly ? "pinned" : "all-records"} onValueChange={(value) => onPinnedOnlyChange(value === "pinned")}>
            <DropdownMenuRadioItem value="all-records">All records</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="pinned">Pinned only</DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      <DropdownMenu>
        <DropdownMenuTrigger asChild><Button variant="ghost" size="sm" className="rounded-l-none"><ArrowUpDown /> Sort</Button></DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-52">
          <DropdownMenuLabel>Sort by</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={sortValue || "default"} onValueChange={(value) => onSortChange(value === "default" ? "" : value)}>
            <DropdownMenuRadioItem value="default">Default order</DropdownMenuRadioItem>
            {sortOptions.map((option) => <DropdownMenuRadioItem key={option.value} value={option.value}>{option.label}</DropdownMenuRadioItem>)}
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
