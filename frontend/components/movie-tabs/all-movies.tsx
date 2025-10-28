"use client"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  Film,
  Trash2,
  Edit,
  Plus,
  Search,
  Filter,
  ExternalLink,
  CheckCircle,
  XCircle,
  Download,
  RefreshCw,
  Archive,
  Settings,
  Cloud,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { DynamicFilterBuilder } from "../dynamic-filter-builder"
import { MovieAPI, type Movie, type MovieListParams, type FilterSchemaItem } from "@/lib/movie-api"
import { toast } from "@/hooks/use-toast"
import { CustomWorkflowModal, type CustomWorkflowConfig } from "../custom-workflow-modal" // Import custom workflow modal
import { ExportDataModal } from "../export-data-modal"

interface AllMoviesProps {
  onEdit: (movie: Movie) => void
  onDelete: (doubanId: string) => void
}

const MOCK_FILTER_SCHEMA: FilterSchemaItem[] = [
  { name: "title", label: "标题", type: "string" },
  {
    name: "category",
    label: "分类",
    type: "enum",
    options: ["China", "Japan", "Korea", "Europe", "Animation", "Other"],
  },
  { name: "movie_type", label: "类型", type: "enum", options: ["TV", "Movie", "Other"] },
  { name: "year", label: "年份", type: "string" },
  { name: "season", label: "季信息", type: "string" },
  { name: "total_episodes", label: "总集数", type: "integer" },
  { name: "has_cloud_info", label: "有网盘信息", type: "boolean" },
  { name: "has_episodes", label: "有剧集信息", type: "boolean" },
]

export function AllMovies({ onEdit, onDelete }: AllMoviesProps) {
  const [movies, setMovies] = useState<Movie[]>([])
  const [loading, setLoading] = useState(true)
  const [filterSchema, setFilterSchema] = useState<FilterSchemaItem[]>(MOCK_FILTER_SCHEMA)
  const [filters, setFilters] = useState<MovieListParams>({ sort_by: "-pubdate" })
  const [selectedMovies, setSelectedMovies] = useState<Set<string>>(new Set())
  const [selectAll, setSelectAll] = useState(false)
  const [showCloudSyncModal, setShowCloudSyncModal] = useState(false)
  const [showExportModal, setShowExportModal] = useState(false)
  const [showUpdateMetaData, setShowUpdateMetaData] = useState(false)
  const [publishModal, setpublishModal] = useState(false)
  const [expandedClouds, setExpandedClouds] = useState<Set<string>>(new Set())
  // Return progress info for all cloud_infos (may be multiple)
  const getCloudProgress = (movie: Movie) => {
    if (!movie.cloud_infos || movie.cloud_infos.length === 0) {
      return null
    }

    const totalEpisodes = movie.episodes_info?.length || 0
    if (totalEpisodes === 0) return null

    return movie.cloud_infos.map((cloudInfo) => {
      const latestEpisode = cloudInfo.latest_episode_number || 0
      const progress = Math.round((latestEpisode / totalEpisodes) * 100)
      return {
        current: latestEpisode,
        total: totalEpisodes,
        progress,
        cloudInfo,
      }
    })
  }

  const toggleExpand = (doubanId: string) => {
    setExpandedClouds((prev) => {
      const next = new Set(prev)
      if (next.has(doubanId)) next.delete(doubanId)
      else next.add(doubanId)
      return next
    })
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case "TV":
        return "bg-blue-100 text-blue-800"
      case "Movie":
        return "bg-green-100 text-green-800"
      case "Other":
        return "bg-gray-100 text-gray-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "China":
        return "bg-red-100 text-red-800"
      case "Japan":
        return "bg-pink-100 text-pink-800"
      case "Korea":
        return "bg-purple-100 text-purple-800"
      case "Europe":
        return "bg-indigo-100 text-indigo-800"
      case "Animation":
        return "bg-yellow-100 text-yellow-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const loadFilterSchema = async () => {
    try {
      const schema = await MovieAPI.getFilterSchema()
      setFilterSchema(schema)
    } catch (error) {
      console.log("[v0] Filter schema API failed, using mock data")
      setFilterSchema(MOCK_FILTER_SCHEMA)
      toast({
        title: "筛选器加载失败",
        description: "使用默认筛选选项，部分功能可能受限",
        variant: "destructive",
      })
    }
  }

  const loadMovies = async () => {
    try {
      setLoading(true)
      const data = await MovieAPI.listMovies(filters)
      setMovies(data)
    } catch (error) {
      toast({
        title: "加载失败",
        description: "无法加载影视列表",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMovies()
    loadFilterSchema()
  }, [filters])

  // Sorting logic
  const currentSortField = filters.sort_by?.replace(/^-/, "")
  const currentSortOrder = filters.sort_by?.startsWith("-") ? "desc" : "asc"

  const handleSortFieldChange = (newField: string) => {
    if (newField === "none") {
      setFilters((prev) => {
        const { sort_by, ...rest } = prev
        return rest
      })
      return
    }
    const newSortBy = currentSortOrder === "desc" ? `-${newField}` : newField
    setFilters((prev) => ({ ...prev, sort_by: newSortBy as any }))
  }

  const handleSortOrderChange = (newOrder: "asc" | "desc") => {
    const field = currentSortField || "update_time"
    const newSortBy = newOrder === "desc" ? `-${field}` : field
    setFilters((prev) => ({ ...prev, sort_by: newSortBy as any }))
  }

  const handleSelectMovie = (movieId: string, checked: boolean) => {
    const newSelected = new Set(selectedMovies)
    if (checked) {
      newSelected.add(movieId)
    } else {
      newSelected.delete(movieId)
    }
    setSelectedMovies(newSelected)
    setSelectAll(newSelected.size === movies.length && movies.length > 0)
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedMovies(new Set(movies.map((m) => m.douban_id)))
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

  useEffect(() => {
    setSelectedMovies(new Set())
    setSelectAll(false)
  }, [movies])

  const cloudSyncWorkflowConfig: CustomWorkflowConfig<Movie> = {
    workflowName: "根据douban_ids同步网盘",
    title: "同步网盘",
    description: "抓取分享链接并转存到网盘",
    fixedParams: {
      douban_ids: []
    },
    fixedParamsBuilder: (selectedMovies: Movie[]) => {
      const d = selectedMovies.map((movie) => `${movie.douban_id}`)
      return {
        douban_ids: d,
      }
    },
    selectedDataValidator: (selectedMovies: Movie[]) => {
      if (selectedMovies.length === 0) {
        return { valid: false, message: "请先选择影视" }
      }
      return { valid: true }
    },
  }
  const updateMetaDataConfig: CustomWorkflowConfig<Movie> = {
    workflowName: "根据douban_id和movie_type保存影视元数据",
    title: "更新影视元数据",
    description: "更新选中的影视元数据",
    fixedParams: {
      douban_infos: [],
    },
    fixedParamsBuilder: (selectedMovies: Movie[]) => {
      const doubanInfos = selectedMovies.map((movie) => `${movie.douban_id}-${movie.movie_type}`)
      return {
        douban_infos: doubanInfos,
      }
    },
    selectedDataValidator: (selectedMovies: Movie[]) => {
      if (selectedMovies.length === 0) {
        return { valid: false, message: "请先要更新的影视" }
      }
      return { valid: true }
    },
  }
  const publishMovieToPlatformConfig: CustomWorkflowConfig<Movie> = {
    workflowName: "将指定的movie推送到平台",
    title: "推送影视到平台",
    description: "推送选择的movie到指定的平台",
    fixedParams: {
      douban_ids: [],
    },
    fixedParamsBuilder: (selectedMovies: Movie[]) => {
      const doubanInfos = selectedMovies.map((movie) => `${movie.douban_id}`)
      return {
        douban_ids: doubanInfos,
      }
    },
    selectedDataValidator: (selectedMovies: Movie[]) => {
      if (selectedMovies.length === 0) {
        return { valid: false, message: "请先选择影视" }
      }
      return { valid: true }
    },
  }




  return (
    <div className="flex gap-6 h-full">
      {/* Card1: Movie content display - scrollable */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="flex-shrink-0 pb-4">
          <CardTitle className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Film className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold">全部影视</h3>
              <p className="text-sm text-muted-foreground font-normal">共 {movies.length} 部影视</p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-hidden">
          <ScrollArea className="h-[calc(100vh-320px)]">
            <div className="pr-4">
              {loading ? (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                  <p className="mt-4 text-muted-foreground">加载中...</p>
                </div>
              ) : movies.length === 0 ? (
                <div className="text-center py-16">
                  <div className="p-6 bg-muted/50 rounded-full w-24 h-24 mx-auto mb-6 flex items-center justify-center">
                    <Film className="h-12 w-12 text-muted-foreground" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">暂无影视数据</h3>
                  <p className="text-muted-foreground">尝试调整筛选条件或添加新的影视</p>
                </div>
              ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                  {movies.map((movie) => {
                    const cloudProgresses = getCloudProgress(movie)
                    const isSelected = selectedMovies.has(movie.douban_id)
                    return (
                      <Card
                        key={movie.douban_id}
                        className={`group hover:shadow-lg transition-all duration-300 border-border/50 hover:border-primary/30 hover:scale-[1.02] ${isSelected ? "ring-2 ring-primary/50 bg-primary/5" : ""
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
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge className={getTypeColor(movie.movie_type)} variant="secondary">
                                  {movie.movie_type}
                                </Badge>
                                <Badge className={getCategoryColor(movie.category)} variant="secondary">
                                  {movie.category}
                                </Badge>
                              </div>
                            </div>

                            <div>
                              <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2 text-base">
                                {movie.title_season}
                              </h4>
                              <div className="flex items-center gap-2 mt-3">
                                <Badge variant="outline" className="text-xs">
                                  {movie.year}
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                  {movie.total_episodes}集
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                  {movie.douban_id}
                                </Badge>
                              </div>
                            </div>

                            {movie.description && (
                              <p className="text-sm text-muted-foreground line-clamp-2">{movie.description}</p>
                            )}

                            {cloudProgresses && (
                              <div className="space-y-2">
                                <div className="space-y-2 p-3 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-lg border border-blue-200/50 dark:border-blue-800/30">
                                  <div className="flex items-center justify-between text-sm">
                                    <span className="font-medium text-blue-900 dark:text-blue-100">网盘进度</span>
                                    <div className="flex items-center gap-1">
                                      {cloudProgresses[0].cloudInfo.last_save_success ? (
                                        <CheckCircle className="h-3 w-3 text-green-600 dark:text-green-400" />
                                      ) : (
                                        <XCircle className="h-3 w-3 text-red-600 dark:text-red-400" />
                                      )}
                                      <span className="text-blue-700 dark:text-blue-300 font-medium">
                                        {cloudProgresses[0].current}/{cloudProgresses[0].total}
                                      </span>
                                    </div>
                                  </div>
                                  <Progress value={cloudProgresses[0].progress} className="h-2" />
                                  <div className="flex items-center justify-between text-xs text-blue-600 dark:text-blue-400">
                                    <span className="truncate">{cloudProgresses[0].cloudInfo.pancloud_name}</span>
                                    <span>{cloudProgresses[0].progress}%</span>
                                  </div>
                                  <div className="flex gap-1">
                                    {cloudProgresses[0].cloudInfo.last_save_link && (
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 px-2 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                                        onClick={() => cloudProgresses[0].cloudInfo.last_save_link && window.open(cloudProgresses[0].cloudInfo.last_save_link, "_blank")}
                                      >
                                        <ExternalLink className="h-3 w-3 mr-1" />
                                        转存链接
                                      </Button>
                                    )}
                                    {cloudProgresses[0].cloudInfo.share_link && (
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 px-2 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                                        onClick={() => cloudProgresses[0].cloudInfo.share_link && window.open(cloudProgresses[0].cloudInfo.share_link, "_blank")}
                                      >
                                        <ExternalLink className="h-3 w-3 mr-1" />
                                        分享链接
                                      </Button>
                                    )}
                                  </div>
                                </div>

                                {cloudProgresses.length > 1 && (
                                  <div className="mt-2">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 px-2 text-xs text-muted-foreground"
                                      onClick={() => toggleExpand(movie.douban_id)}
                                    >
                                      {expandedClouds.has(movie.douban_id) ? (
                                        <>
                                          <ChevronUp className="h-3 w-3 mr-1" /> 收起
                                        </>
                                      ) : (
                                        <>
                                          <ChevronDown className="h-3 w-3 mr-1" /> 展开全部 ({cloudProgresses.length})
                                        </>
                                      )}
                                    </Button>
                                    {expandedClouds.has(movie.douban_id) && (
                                      <div className="space-y-2 mt-2">
                                        {cloudProgresses.map((cp, idx) => (
                                          <div key={idx} className="p-3 bg-muted/20 rounded-lg border border-border/30 text-xs">
                                            <div className="flex items-center justify-between">
                                              <div className="font-medium">{cp.cloudInfo.pancloud_name}</div>
                                              <div className="flex items-center gap-2">
                                                {cp.cloudInfo.last_save_success ? (
                                                  <CheckCircle className="h-3 w-3 text-green-600 dark:text-green-400" />
                                                ) : (
                                                  <XCircle className="h-3 w-3 text-red-600 dark:text-red-400" />
                                                )}
                                                <span className="font-medium">{cp.current}/{cp.total}</span>
                                              </div>
                                            </div>
                                            <Progress value={cp.progress} className="h-2 mt-2" />
                                            <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground">
                                              <span>{cp.progress}%</span>
                                              <div className="flex gap-1">
                                                {cp.cloudInfo.last_save_link && (
                                                  <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-6 px-2 text-xs"
                                                    onClick={() => cp.cloudInfo.last_save_link && window.open(cp.cloudInfo.last_save_link, "_blank")}
                                                  >
                                                    <ExternalLink className="h-3 w-3 mr-1" /> 转存
                                                  </Button>
                                                )}
                                                {cp.cloudInfo.share_link && (
                                                  <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-6 px-2 text-xs"
                                                    onClick={() => cp.cloudInfo.share_link && window.open(cp.cloudInfo.share_link, "_blank")}
                                                  >
                                                    <ExternalLink className="h-3 w-3 mr-1" /> 分享
                                                  </Button>
                                                )}
                                              </div>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                            {movie.share_links && movie.share_links.length > 0 && (
                              <div className="space-y-2">
                                <h5 className="text-sm font-medium text-muted-foreground">预转存链接</h5>
                                <div className="flex flex-wrap gap-1">
                                  {movie.share_links.slice(0, 2).map((link, index) => (
                                    <Button
                                      key={index}
                                      variant="ghost"
                                      size="sm"
                                      className="h-6 px-2 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                                      onClick={() => window.open(link, "_blank")}
                                    >
                                      <ExternalLink className="h-3 w-3 mr-1" />
                                      链接{index + 1}
                                    </Button>
                                  ))}
                                  {movie.share_links.length > 2 && (
                                    <span className="text-xs text-muted-foreground px-2">
                                      +{movie.share_links.length - 2}
                                    </span>
                                  )}
                                </div>
                              </div>
                            )}

                            <div className="flex items-center justify-between pt-3 border-t border-border/50">
                              <div className="text-xs text-muted-foreground">
                                <div>剧集: {(movie.episodes_info ?? []).length}集</div>
                                <div>更新: {new Date(movie.update_time).toLocaleDateString("zh-CN")}</div>
                              </div>
                              <div className="flex items-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => onEdit(movie)}
                                  className="h-8 px-3 text-xs hover:bg-primary/10 hover:text-primary transition-colors"
                                >
                                  <Edit className="h-3 w-3 mr-1" />
                                  编辑
                                </Button>
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-8 px-3 text-xs hover:bg-destructive/10 hover:text-destructive transition-colors"
                                    >
                                      <Trash2 className="h-3 w-3" />
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>确认删除</AlertDialogTitle>
                                      <AlertDialogDescription>
                                        确定要删除影视《{movie.title_season}》吗？此操作无法撤销。
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>取消</AlertDialogCancel>
                                      <AlertDialogAction onClick={() => onDelete(movie.douban_id)}>
                                        删除
                                      </AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
                              </div>
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

      {/* Card2: Filters and Actions - fixed, no scrolling */}
      <Card className="w-80 flex-shrink-0 flex flex-col">
        <CardHeader className="flex-shrink-0 pb-4">
          <CardTitle className="text-lg">控制面板</CardTitle>
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

                {movies.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <Checkbox id="select-all" checked={selectAll} onCheckedChange={handleSelectAll} />
                    <Label htmlFor="select-all" className="text-sm font-medium">
                      全选 ({selectedMovies.size}/{movies.length})
                    </Label>
                  </div>
                )}

                <div className="grid grid-cols-1 gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowCloudSyncModal(true)}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <Cloud className="h-3 w-3 mr-2" />
                    同步网盘
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowUpdateMetaData(true)}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <RefreshCw className="h-3 w-3 mr-2" />
                    更新元数据
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setpublishModal(true)}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <RefreshCw className="h-3 w-3 mr-2" />
                    发布至平台
                  </Button>


                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowExportModal(true)}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <Download className="h-3 w-3 mr-2" />
                    导出数据
                  </Button>


                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBatchAction("归档")}
                    disabled={selectedMovies.size === 0}
                    className="h-8 justify-start"
                  >
                    <Archive className="h-3 w-3 mr-2" />
                    归档
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
                  <div className="grid grid-cols-2 gap-2">
                    <Button variant="outline" size="sm" className="h-8 bg-transparent">
                      <Plus className="h-3 w-3 mr-1" />
                      添加影视
                    </Button>
                    <Button variant="outline" size="sm" className="h-8 bg-transparent" onClick={loadMovies}>
                      <RefreshCw className="h-3 w-3 mr-1" />
                      刷新列表
                    </Button>
                  </div>
                </div>
              </div>

              {/* Filters Section */}
              <div className="space-y-4 pt-4 border-t">
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4" />
                  <h4 className="font-medium text-base">筛选条件</h4>
                </div>

                <DynamicFilterBuilder schema={filterSchema} filters={filters} onFiltersChange={setFilters} />

                <div className="space-y-3">
                  <div>
                    <Label htmlFor="sort-filter" className="text-sm">
                      排序
                    </Label>
                    <Select value={currentSortField || "pubdate"} onValueChange={handleSortFieldChange}>
                      <SelectTrigger className="h-8">
                        <SelectValue placeholder="选择排序字段" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pubdate">上映时间</SelectItem>
                        <SelectItem value="update_time">更新时间</SelectItem>
                        <SelectItem value="create_time">创建时间</SelectItem>
                        <SelectItem value="year">年份</SelectItem>
                        <SelectItem value="none">不排序</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="sort-order-filter" className="text-sm">
                      排序方向
                    </Label>
                    <Select
                      value={currentSortOrder}
                      onValueChange={(value) => handleSortOrderChange(value as "asc" | "desc")}
                      disabled={!currentSortField}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue placeholder="选择排序方向" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="desc">降序</SelectItem>
                        <SelectItem value="asc">升序</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="limit-filter" className="text-sm">
                      每页数量
                    </Label>
                    <Select
                      value={filters.limit?.toString() || "50"}
                      onValueChange={(value) => setFilters((prev) => ({ ...prev, limit: Number.parseInt(value) }))}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue placeholder="选择每页数量" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="25">25</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button onClick={loadMovies} className="w-full h-8" size="sm">
                  <Search className="h-4 w-4 mr-2" />
                  应用筛选并搜索
                </Button>
              </div>
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <CustomWorkflowModal
        open={showCloudSyncModal}
        onOpenChange={setShowCloudSyncModal}
        config={cloudSyncWorkflowConfig}
        selectedData={movies.filter((m) => selectedMovies.has(m.douban_id))}
        onTaskCreated={() => {
          setShowCloudSyncModal(false)
          toast({
            title: "任务已创建",
            description: "正在后台处理中",
          })
        }}
      />

      <CustomWorkflowModal
        open={showUpdateMetaData}
        onOpenChange={setShowUpdateMetaData}
        config={updateMetaDataConfig}
        selectedData={movies.filter((m) => selectedMovies.has(m.douban_id))}
        onTaskCreated={() => {
          setShowUpdateMetaData(false)
          toast({
            title: "任务已创建",
            description: "正在后台处理中",
          })
        }}
      />

      <CustomWorkflowModal
        open={publishModal}
        onOpenChange={setpublishModal}
        config={publishMovieToPlatformConfig}
        selectedData={movies.filter((m) => selectedMovies.has(m.douban_id))}
        onTaskCreated={() => {
          setpublishModal(false)
          toast({
            title: "任务已创建",
            description: "正在后台处理中",
          })
        }}
      />


      <ExportDataModal
        open={showExportModal}
        onOpenChange={setShowExportModal}
        selectedMovies={movies.filter((m) => selectedMovies.has(m.douban_id))}
      />
    </div>
  )
}
