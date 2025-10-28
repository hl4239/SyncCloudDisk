"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface Tab {
  id: string
  label: string
  icon: LucideIcon
}

interface SidebarProps {
  tabs: Tab[]
  activeTab: string
  onTabChange: (tabId: string) => void
}

export function Sidebar({ tabs, activeTab, onTabChange }: SidebarProps) {
  return (
    <div className="w-64 border-r bg-sidebar flex-shrink-0">
      <div className="p-4">
        <Card>
          <CardContent className="p-2">
            <div className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <Button
                    key={tab.id}
                    variant={activeTab === tab.id ? "default" : "ghost"}
                    size="sm"
                    onClick={() => onTabChange(tab.id)}
                    className={cn(
                      "w-full justify-start gap-3 h-10 px-3",
                      "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors",
                      activeTab === tab.id && "bg-sidebar-primary text-sidebar-primary-foreground",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </Button>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
