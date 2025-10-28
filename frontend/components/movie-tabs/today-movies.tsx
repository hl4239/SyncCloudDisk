"use client"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Calendar, Edit, ExternalLink, CheckCircle, XCircle, ChevronDown, ChevronUp } from "lucide-react"
import { MovieAPI, type Movie } from "@/lib/movie-api"

interface TodayMoviesProps {
  onEdit: (movie: Movie) => void
}

export function TodayMovies({ onEdit }: TodayMoviesProps) {
  const [todayMovies, setTodayMovies] = useState<Movie[]>([])
  const [loadingToday, setLoadingToday] = useState(true)
  const [expandedClouds, setExpandedClouds] = useState<Set<string>>(new Set())

const getShanghaiTodayStr = () => {
  const now = new Date();
  
  // 使用 Intl.DateTimeFormat 直接在指定时区格式化日期。
  // 'sv-SE' (瑞典) locale 格式为 YYYY-MM-DD，非常适合直接使用。
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Shanghai',
  }).format(now);
};

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

  const loadTodayMovies = async () => {
    try {
      setLoadingToday(true)
      const data = await MovieAPI.listTodayMovies()
      setTodayMovies(data)
    } catch (error) {
      console.error("Failed to load today's movies:", error)
    } finally {
      setLoadingToday(false)
    }
  }

  useEffect(() => {
    loadTodayMovies()
  }, [])

  const todayStr = getShanghaiTodayStr()

  return (
    <Card className="bg-gradient-to-r from-primary/5 to-secondary/5 border-primary/20">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-3 text-primary">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold">今日追剧</h3>
            <p className="text-sm text-muted-foreground font-normal">{todayStr}</p>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loadingToday ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
            <span className="ml-3 text-muted-foreground">加载今日剧集...</span>
          </div>
        ) : todayMovies.length === 0 ? (
          <div className="text-center py-16">
            <div className="p-6 bg-muted/50 rounded-full w-24 h-24 mx-auto mb-6 flex items-center justify-center">
              <Calendar className="h-12 w-12 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold mb-2">今天没有剧集更新</h3>
            <p className="text-muted-foreground">享受悠闲时光吧 ✨</p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
            {todayMovies.map((m) => {
              const epsToday = (m.episodes_info || []).filter((ep) => ep.air_date === todayStr)
              const cloudProgresses = getCloudProgress(m)
              const isExpanded = expandedClouds.has(m.douban_id)
              return (
                <Card
                  key={m.douban_id}
                  className="group hover:shadow-lg transition-all duration-300 border-border/50 hover:border-primary/30 hover:scale-[1.02]"
                >
                  <CardContent className="p-5">
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2 text-base">
                          {m.title_season}
                        </h4>
                        <div className="flex items-center gap-2 mt-3">
                          <Badge variant="secondary" className="text-xs font-medium">
                            {m.category}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {m.year}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {m.douban_id}
                          </Badge>
                        </div>
                      </div>

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
                            <span>{cloudProgresses[0].cloudInfo.pancloud_name}</span>
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
                                onClick={() => toggleExpand(m.douban_id)}
                              >
                                {isExpanded ? (
                                  <>
                                    <ChevronUp className="h-3 w-3 mr-1" /> 收起
                                  </>
                                ) : (
                                  <>
                                    <ChevronDown className="h-3 w-3 mr-1" /> 展开全部 ({cloudProgresses.length})
                                  </>
                                )}
                              </Button>
                              {isExpanded && (
                                <div className="space-y-2 mt-2">
                                  {cloudProgresses.map((cp, idx) => (
                                    <div
                                      key={idx}
                                      className="p-3 bg-muted/20 rounded-lg border border-border/30 text-xs"
                                    >
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
                                              onClick={() => window.open(cp.cloudInfo.last_save_link, "_blank")}
                                            >
                                              <ExternalLink className="h-3 w-3 mr-1" /> 转存
                                            </Button>
                                          )}
                                          {cp.cloudInfo.share_link && (
                                            <Button
                                              variant="ghost"
                                              size="sm"
                                              className="h-6 px-2 text-xs"
                                              onClick={() => window.open(cp.cloudInfo.share_link, "_blank")}
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

                      <div className="space-y-3">
                        {epsToday.map((ep) => (
                          <div
                            key={ep.episode_number}
                            className="flex items-center justify-between p-3 bg-gradient-to-r from-muted/40 to-muted/20 rounded-lg border border-border/30"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 bg-primary/15 rounded-full flex items-center justify-center">
                                <span className="text-sm font-semibold text-primary">{ep.episode_number}</span>
                              </div>
                              <span className="text-sm font-medium">第{ep.episode_number}集</span>
                            </div>
                            {ep.air_time && (
                              <Badge variant="outline" className="text-xs font-medium">
                                {ep.air_time}
                              </Badge>
                            )}
                          </div>
                        ))}
                      </div>

                      <div className="flex items-center justify-between pt-3 border-t border-border/50">
                        <div className="text-xs text-muted-foreground font-medium">共 {epsToday.length} 集更新</div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onEdit(m)}
                          className="h-8 px-3 text-xs hover:bg-primary/10 hover:text-primary transition-colors"
                        >
                          <Edit className="h-3 w-3 mr-1" />
                          编辑
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
