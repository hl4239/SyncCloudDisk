"use client"

import { CommandEmpty } from "@/components/ui/command"

import { useState } from "react"
import type { MovieListParams, FilterSchemaItem } from "@/lib/movie-api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandList, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command"
import { PlusCircle, X } from "lucide-react"

interface DynamicFilterBuilderProps {
  schema: FilterSchemaItem[]
  filters: MovieListParams
  onFiltersChange: (newFilters: MovieListParams) => void
}

export function DynamicFilterBuilder({ schema, filters, onFiltersChange }: DynamicFilterBuilderProps) {
  const safeSchema = Array.isArray(schema) ? schema : []

  const [activeFilterKeys, setActiveFilterKeys] = useState<string[]>(() =>
    // Initialize with keys that are already present in the filters, excluding sorting/pagination
    Object.keys(filters).filter((key) => !["limit", "offset", "sort_by", "sort_order"].includes(key)),
  )

  const handleAddFilter = (filterName: string) => {
    if (!activeFilterKeys.includes(filterName)) {
      setActiveFilterKeys([...activeFilterKeys, filterName])
    }
  }

  const handleRemoveFilter = (filterName: string) => {
    setActiveFilterKeys(activeFilterKeys.filter((key) => key !== filterName))
    const { [filterName]: _, ...rest } = filters as any
    onFiltersChange(rest)
  }

  const handleFilterValueChange = (filterName: string, value: any) => {
    if (value === "" || value === undefined || value === null) {
      const { [filterName]: _, ...rest } = filters as any
      onFiltersChange(rest)
    } else {
      onFiltersChange({ ...filters, [filterName]: value })
    }
  }

  const renderFilterInput = (key: string) => {
    const spec = safeSchema.find((s) => s.name === key)
    if (!spec) return null

    const value = (filters as any)[key]

    switch (spec.type) {
      case "boolean":
        return (
          <Select value={value?.toString() ?? ""} onValueChange={(val) => handleFilterValueChange(key, val === "true")}>
            <SelectTrigger>
              <SelectValue placeholder="Select..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="true">Yes</SelectItem>
              <SelectItem value="false">No</SelectItem>
            </SelectContent>
          </Select>
        )
      case "enum":
        return (
          <Select value={value ?? ""} onValueChange={(val) => handleFilterValueChange(key, val)}>
            <SelectTrigger>
              <SelectValue placeholder="Select..." />
            </SelectTrigger>
            <SelectContent>
              {spec.options?.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )
      case "integer":
        return (
          <Input
            type="number"
            placeholder="Enter a number..."
            value={value || ""}
            onChange={(e) => handleFilterValueChange(key, e.target.value ? Number(e.target.value) : undefined)}
          />
        )
      case "string":
      default:
        return (
          <Input
            placeholder="Enter text..."
            value={value || ""}
            onChange={(e) => handleFilterValueChange(key, e.target.value)}
          />
        )
    }
  }

  const availableFilters = safeSchema.filter((s) => !activeFilterKeys.includes(s.name))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {activeFilterKeys.map((key) => {
          const spec = safeSchema.find((s) => s.name === key)
          if (!spec) return null
          return (
            <div key={key} className="flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor={key} className="text-sm font-medium">
                  {spec.label}
                </Label>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => handleRemoveFilter(key)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {renderFilterInput(key)}
            </div>
          )
        })}
      </div>

      {availableFilters.length > 0 && (
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline">
              <PlusCircle className="h-4 w-4 mr-2" />
              Add Filter
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64 p-0">
            <Command>
              <CommandInput placeholder="Search filter..." />
              <CommandList>
                <CommandEmpty>No filter found.</CommandEmpty>
                <CommandGroup>
                  {availableFilters.map((spec) => (
                    <CommandItem
                      key={spec.name}
                      onSelect={() => {
                        handleAddFilter(spec.name)
                      }}
                    >
                      {spec.label}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      )}
    </div>
  )
}
