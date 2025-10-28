import React from "react"
import type { Movie, CloudInfo } from "@/lib/movie-api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Copy } from "lucide-react"

export interface ExportTemplate {
  name: string
  description: string
  export: (movies: Movie[]) => ExportResult
  // 可选：自定义渲染导出结果的函数，返回 JSX
  renderResult?: (data: any, onCopy: (text: string, fieldName: string) => void) => React.ReactNode
}

export interface ExportResult {
  success: boolean
  data?: any
  error?: string
}

/**
 * 爱盘搜资源提交模板
 * 将选中的Movie的cloud_infos中的share_link按照平台分类并拼接
 */
export const AipanTemplate: ExportTemplate = {
  name: "爱盘搜资源提交模板",
  description: "将分享链接按照平台分类（夸克、百度）并导出",

  export: (movies: Movie[]): ExportResult => {
    try {
      // 1. 合并所有Movie的cloud_infos数组
      const allCloudInfos: CloudInfo[] = []
      movies.forEach((movie) => {
        if (movie.cloud_infos && Array.isArray(movie.cloud_infos)) {
          allCloudInfos.push(...movie.cloud_infos)
        }
      })

      // 2. 筛选出含有内容的share_link
      const validShareLinks = allCloudInfos
        .filter((info) => info.share_link && info.share_link.trim() !== "")
        .map((info) => info.share_link as string)

      // 3. 按照share_link内容分类
      const quarkLinks: string[] = []
      const baiduLinks: string[] = []
      const otherLinks: string[] = []

      validShareLinks.forEach((link) => {
        if (link.toLowerCase().includes("quark")) {
          quarkLinks.push(link)
        } else if (link.toLowerCase().includes("baidu")) {
          baiduLinks.push(link)
        } else {
          otherLinks.push(link)
        }
      })

      // 4. 每组内部用','分隔符拼接
      const result = {
        quark: quarkLinks.join(","),
        baidu: baiduLinks.join(","),
        other: otherLinks.join(","),
        summary: {
          totalMovies: movies.length,
          totalCloudInfos: allCloudInfos.length,
          validShareLinks: validShareLinks.length,
          quarkCount: quarkLinks.length,
          baiduCount: baiduLinks.length,
          otherCount: otherLinks.length,
        },
      }

      return {
        success: true,
        data: result,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "导出失败",
      }
    }
  },
  // 自定义结果渲染器：把原来导出模态中的爱盘结果布局搬到这里
  renderResult: (exportResult: any, onCopy: (text: string, fieldName: string) => void) => {
    if (!exportResult) return null

    return (
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">导出结果（爱盘搜模板）</CardTitle>
            <CardDescription>按平台分类并整理的分享链接</CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline">
              <a href="https://aipanso.com/submitRes" target="_blank" rel="noreferrer">提交到爱盘搜</a>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[300px]">
            <div className="space-y-4">
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

              {exportResult.quark && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">夸克网盘链接</h4>
                    <Button size="sm" variant="ghost" onClick={() => onCopy(exportResult.quark, "夸克链接")}>
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="p-3 bg-muted rounded-lg text-sm break-all">{exportResult.quark || "无"}</div>
                </div>
              )}

              {exportResult.baidu && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">百度网盘链接</h4>
                    <Button size="sm" variant="ghost" onClick={() => onCopy(exportResult.baidu, "百度链接")}>
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="p-3 bg-muted rounded-lg text-sm break-all">{exportResult.baidu || "无"}</div>
                </div>
              )}

              {exportResult.other && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">其他平台链接</h4>
                    <Button size="sm" variant="ghost" onClick={() => onCopy(exportResult.other, "其他链接")}>
                      <Copy className="h-4 w-4" />
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
  },
}
