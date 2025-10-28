"use client"

import { useState } from "react"
import type { Movie } from "@/lib/movie-api"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Download, Copy, Check } from "lucide-react"
import { EXPORT_TEMPLATES } from "./export-templates"
import { toast } from "sonner"

interface ExportDataModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  selectedMovies: Movie[]
}

export function ExportDataModal({ open, onOpenChange, selectedMovies }: ExportDataModalProps) {
  const [selectedTemplate, setSelectedTemplate] = useState(EXPORT_TEMPLATES[0]?.name || "")
  const [exportResult, setExportResult] = useState<any>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)

  const handleExport = () => {
    const template = EXPORT_TEMPLATES.find((t) => t.name === selectedTemplate)
    if (!template) {
      toast.error("未找到导出模板")
      return
    }

    const result = template.export(selectedMovies)
    if (result.success) {
      setExportResult(result.data)
      toast.success("导出成功")
    } else {
      toast.error(result.error || "导出失败")
    }
  }

  const handleCopy = async (text: string, fieldName: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedField(fieldName)
      toast.success(`已复制${fieldName}`)
      setTimeout(() => setCopiedField(null), 2000)
    } catch (error) {
      toast.error("复制失败")
    }
  }

  const handleDownload = () => {
    if (!exportResult) return

    const dataStr = JSON.stringify(exportResult, null, 2)
    const blob = new Blob([dataStr], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `export-${selectedTemplate}-${new Date().getTime()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success("下载成功")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>导出数据</DialogTitle>
          <DialogDescription>已选择 {selectedMovies.length} 个影视资源</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 模板选择 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">选择导出模板</label>
            <Tabs value={selectedTemplate} onValueChange={setSelectedTemplate}>
              <TabsList
                className="grid w-full"
                style={{ gridTemplateColumns: `repeat(${EXPORT_TEMPLATES.length}, 1fr)` }}
              >
                {EXPORT_TEMPLATES.map((template) => (
                  <TabsTrigger key={template.name} value={template.name}>
                    {template.name}
                  </TabsTrigger>
                ))}
              </TabsList>
              {EXPORT_TEMPLATES.map((template) => (
                <TabsContent key={template.name} value={template.name} className="mt-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">{template.name}</CardTitle>
                      <CardDescription>{template.description}</CardDescription>
                    </CardHeader>
                  </Card>
                </TabsContent>
              ))}
            </Tabs>
          </div>

          {/* 导出按钮 */}
          <div className="flex gap-2">
            <Button onClick={handleExport} className="flex-1">
              <Download className="mr-2 h-4 w-4" />
              执行导出
            </Button>
            {exportResult && (
              <Button onClick={handleDownload} variant="outline">
                <Download className="mr-2 h-4 w-4" />
                下载JSON
              </Button>
            )}
          </div>

          {/* 导出结果 */}
          {exportResult && (
            // 如果当前模板提供自定义渲染器，则使用它；否则使用通用布局
            (EXPORT_TEMPLATES.find((t) => t.name === selectedTemplate)?.renderResult
              ? (EXPORT_TEMPLATES.find((t) => t.name === selectedTemplate) as any).renderResult(exportResult, handleCopy)
              : (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">导出结果</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[300px]">
                      <div className="space-y-4">
                        {/* 统计信息 */}
                        {exportResult.summary && (
                          <div className="p-3 bg-muted rounded-lg">
                            <h4 className="font-medium mb-2">统计信息</h4>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div>总影视数: {exportResult.summary.totalMovies}</div>
                              <div>总云盘信息: {exportResult.summary.totalCloudInfos}</div>
                              <div>有效分享链接: {exportResult.summary.validShareLinks}</div>
                              <div>夸克链接: {exportResult.summary.quarkCount}</div>
                              <div>百度链接: {exportResult.summary.baiduCount}</div>
                              <div>其他链接: {exportResult.summary.otherCount}</div>
                            </div>
                          </div>
                        )}

                        {/* 夸克链接 */}
                        {exportResult.quark && (
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium">夸克网盘链接</h4>
                              <Button size="sm" variant="ghost" onClick={() => handleCopy(exportResult.quark, "夸克链接")}>
                                {copiedField === "夸克链接" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                              </Button>
                            </div>
                            <div className="p-3 bg-muted rounded-lg text-sm break-all">{exportResult.quark || "无"}</div>
                          </div>
                        )}

                        {/* 百度链接 */}
                        {exportResult.baidu && (
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium">百度网盘链接</h4>
                              <Button size="sm" variant="ghost" onClick={() => handleCopy(exportResult.baidu, "百度链接")}>
                                {copiedField === "百度链接" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                              </Button>
                            </div>
                            <div className="p-3 bg-muted rounded-lg text-sm break-all">{exportResult.baidu || "无"}</div>
                          </div>
                        )}

                        {/* 其他链接 */}
                        {exportResult.other && (
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium">其他平台链接</h4>
                              <Button size="sm" variant="ghost" onClick={() => handleCopy(exportResult.other, "其他链接")}>
                                {copiedField === "其他链接" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                              </Button>
                            </div>
                            <div className="p-3 bg-muted rounded-lg text-sm break-all">{exportResult.other || "无"}</div>
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              )
            )
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
