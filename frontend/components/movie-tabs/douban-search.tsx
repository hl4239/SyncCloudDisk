"use client"
import { useState } from "react"
import type React from "react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { ProxyImage } from "@/components/ui/proxy-image"
import { Search, Plus, Download, Archive, Settings, RefreshCw, Database } from "lucide-react"
import { toast } from "@/hooks/use-toast"
import { CustomWorkflowModal, type CustomWorkflowConfig } from "@/components/custom-workflow-modal"
import { MovieAPI, type Movie, DoubanMovie } from "@/lib/movie-api"


export function DoubanSearch() {
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<DoubanMovie[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedMovies, setSelectedMovies] = useState<Set<string>>(new Set())
  const [selectAll, setSelectAll] = useState(false)
  const [customWorkflowOpen, setCustomWorkflowOpen] = useState(false)

  const searchDouban = async () => {
    if (!searchQuery.trim()) {
      toast({
        title: "请输入搜索关键词",
        description: "请输入要搜索的影视名称",
        variant: "destructive",
      })
      return
    }

    try {
      setLoading(true)
     
      const data=await MovieAPI.searchDouban(searchQuery)
      setSearchResults(data)
      setSelectedMovies(new Set())
      setSelectAll(false)
    } catch (error) {
      toast({
        title: "搜索失败",
        description: "无法连接到豆瓣搜索服务",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      searchDouban()
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case "TV":
        return "bg-blue-100 text-blue-800"
      case "Movie":
        return "bg-green-100 text-green-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const handleSelectMovie = (movieId: string, checked: boolean) => {
    const newSelected = new Set(selectedMovies)
    if (checked) {
      newSelected.add(movieId)
    } else {
      newSelected.delete(movieId)
    }
    setSelectedMovies(newSelected)
    setSelectAll(newSelected.size === searchResults.length && searchResults.length > 0)
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedMovies(new Set(searchResults.map((m) => m.douban_id)))
    } else {
      setSelectedMovies(new Set())
    }
    setSelectAll(checked)
  }

  const handleBatchAction = (action: string) => {
    const selectedCount = selectedMovies.size
    if (selectedCount === 0) {
      toast({
        title: "未选择影视",
        description: "请先选择要操作的影视",
        variant: "destructive",
      })
      return
    }

    toast({
      title: `批量操作: ${action}`,
      description: `将对 ${selectedCount} 部影视执行 ${action} 操作`,
    })
  }

  const doubanStorageConfig: CustomWorkflowConfig<DoubanMovie> = {
    workflowName: "根据douban_id和movie_type保存影视元数据",
    title: "豆瓣影视入库",
    description: "将选中的豆瓣影视数据保存到数据库中",
    fixedParams: {
      douban_infos: [],
    },
    fixedParamsBuilder: (selectedMovies: DoubanMovie[]) => {
      const doubanInfos = selectedMovies.map((movie) => `${movie.douban_id}-${movie.movie_type}`)
      return {
        douban_infos: doubanInfos,
      }
    },
    selectedDataValidator: (selectedMovies: DoubanMovie[]) => {
      if (selectedMovies.length === 0) {
        return { valid: false, message: "请先选择要入库的影视" }
      }
      return { valid: true }
    },
  }

  const handleStorageAction = () => {
    const selectedMoviesList = searchResults.filter((movie) => selectedMovies.has(movie.douban_id))

    if (selectedMoviesList.length === 0) {
      toast({
        title: "未选择影视",
        description: "请先选择要入库的影视",
        variant: "destructive",
      })
      return
    }

    setCustomWorkflowOpen(true)
  }

  return (
    <div className="flex gap-6 h-full">
      {/* Card1: Search results display - scrollable */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="flex-shrink-0 pb-4">
          <CardTitle className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Search className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold">豆瓣搜索</h3>
              <p className="text-sm text-muted-foreground font-normal">
                {searchResults.length > 0 ? `找到 ${searchResults.length} 个结果` : "搜索豆瓣影视资源"}
              </p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-hidden">
          {/* Search input */}
          <div className="flex gap-2 mb-4">
            <Input
              placeholder="输入影视名称搜索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1"
            />
            <Button onClick={searchDouban} disabled={loading}>
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent mr-2" />
              ) : (
                <Search className="h-4 w-4 mr-2" />
              )}
              搜索
            </Button>
          </div>

          <ScrollArea className="h-[calc(100vh-400px)]">
            <div className="pr-4">
              {loading ? (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                  <p className="mt-4 text-muted-foreground">搜索中...</p>
                </div>
              ) : searchResults.length === 0 ? (
                <div className="text-center py-16">
                  <div className="p-6 bg-muted/50 rounded-full w-24 h-24 mx-auto mb-6 flex items-center justify-center">
                    <Search className="h-12 w-12 text-muted-foreground" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">开始搜索</h3>
                  <p className="text-muted-foreground">输入关键词搜索豆瓣影视资源</p>
                </div>
              ) : (
                <div className="grid gap-6 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8">
                  {searchResults.map((movie) => {
                    const isSelected = selectedMovies.has(movie.douban_id)
                    return (
                      <Card
                        key={movie.douban_id}
                        className={`group hover:shadow-lg transition-all duration-300 border-border/50 hover:border-primary/30 hover:scale-[1.02] ${
                          isSelected ? "ring-2 ring-primary/50 bg-primary/5" : ""
                        }`}
                      >
                        <CardContent className="p-5">
                          <div className="space-y-4">
                            <div className="flex items-start justify-between">
                              <Checkbox
                                checked={isSelected}
                                onCheckedChange={(checked) => handleSelectMovie(movie.douban_id, checked as boolean)}
                                className="mt-1"
                              />
                              <Badge className={getTypeColor(movie.movie_type)} variant="secondary">
                                {movie.movie_type}
                              </Badge>
                            </div>

                            {movie.pic && (
                              <div className="aspect-[3/4] overflow-hidden rounded-lg bg-muted">
                                <ProxyImage
                                  src={movie.pic}
                                  alt={movie.title}
                                  className="aspect-[3/4] overflow-hidden rounded-lg"
                                />
                              </div>
                            )}

                            <div>
                              <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2 text-base">
                                {movie.title}
                              </h4>
                              <div className="flex items-center gap-2 mt-3">
                                <Badge variant="outline" className="text-xs">
                                  {movie.year}
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                  豆瓣ID: {movie.douban_id}
                                </Badge>
                              </div>
                            </div>

                            <div className="flex items-center justify-between pt-3 border-t border-border/50">
                              <div className="text-xs text-muted-foreground">
                                <div>类型: {movie.movie_type === "TV" ? "电视剧" : "电影"}</div>
                                <div>年份: {movie.year}</div>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-3 text-xs hover:bg-primary/10 hover:text-primary transition-colors"
                                onClick={() => {
                                  toast({
                                    title: "添加到收藏",
                                    description: `已添加《${movie.title}》到收藏列表`,
                                  })
                                }}
                              >
                                <Plus className="h-3 w-3 mr-1" />
                                添加
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Card2: Search controls and Actions - fixed, no scrolling */}
      <Card className="w-80 flex-shrink-0 flex flex-col">
        <CardHeader className="flex-shrink-0 pb-4">
          <CardTitle className="text-lg">搜索控制</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0">
          <ScrollArea className="h-[calc(100vh-320px)] pr-4">
            <div className="space-y-4">
              {/* Selection and Actions Section */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-base">选择与操作</h4>
                  {selectedMovies.size > 0 && (
                    <Badge variant="secondary" className="bg-primary/10 text-primary">
                      已选择 {selectedMovies.size} 部
                    </Badge>
                  )}
                </div>

                {searchResults.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <Checkbox id="select-all-douban" checked={selectAll} onCheckedChange={handleSelectAll} />
                    <Label htmlFor="select-all-douban" className="text-sm font-medium">
                      全选 ({selectedMovies.size}/{searchResults.length})
                    </Label>
                  </div>
                )}

                <div className="grid grid-cols-1 gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleStorageAction}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start bg-primary hover:bg-primary/90"
                  >
                    <Database className="h-3 w-3 mr-2" />
                    入库
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBatchAction("批量添加")}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <Plus className="h-3 w-3 mr-2" />
                    批量添加
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBatchAction("导出数据")}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <Download className="h-3 w-3 mr-2" />
                    导出数据
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBatchAction("收藏")}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <Archive className="h-3 w-3 mr-2" />
                    收藏
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBatchAction("批量设置")}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <Settings className="h-3 w-3 mr-2" />
                    批量设置
                  </Button>
                </div>

                <div className="pt-3 border-t">
                  <Button variant="outline" size="sm" className="w-full h-8 bg-transparent" onClick={searchDouban}>
                    <RefreshCw className="h-3 w-3 mr-1" />
                    重新搜索
                  </Button>
                </div>
              </div>

              {/* Search Tips Section */}
              <div className="space-y-4 pt-4 border-t">
                <h4 className="font-medium text-base">搜索提示</h4>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p>• 支持中文和英文影视名称搜索</p>
                  <p>• 可搜索电视剧和电影</p>
                  <p>• 搜索结果包含豆瓣评分和基本信息</p>
                  <p>• 点击"添加"可将影视加入管理列表</p>
                </div>
              </div>

              {/* Search History Section */}
              <div className="space-y-4 pt-4 border-t">
                <h4 className="font-medium text-base">搜索历史</h4>
                <div className="space-y-1">
                  <Button variant="ghost" size="sm" className="w-full justify-start h-8 text-xs">
                    鬼吹灯
                  </Button>
                  <Button variant="ghost" size="sm" className="w-full justify-start h-8 text-xs">
                    庆余年
                  </Button>
                  <Button variant="ghost" size="sm" className="w-full justify-start h-8 text-xs">
                    三体
                  </Button>
                </div>
              </div>
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <CustomWorkflowModal
        open={customWorkflowOpen}
        onOpenChange={setCustomWorkflowOpen}
        onTaskCreated={() => {
          setCustomWorkflowOpen(false)
          toast({
            title: "入库任务已创建",
            description: "影视数据正在后台处理中",
          })
        }}
        config={doubanStorageConfig}
        selectedData={searchResults.filter((movie) => selectedMovies.has(movie.douban_id))}
      />
    </div>
  )
}
