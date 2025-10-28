"use client"
import { useState } from "react"
import type React from "react"

interface ProxyImageProps {
  src: string
  alt: string
  className?: string
  onError?: (e: React.SyntheticEvent<HTMLImageElement, Event>) => void
}

export function ProxyImage({ src, alt, className, onError }: ProxyImageProps) {
  const [imageError, setImageError] = useState(false)
  const [loading, setLoading] = useState(true)

  // 使用多种代理策略
  const getProxiedUrl = (originalUrl: string) => {
    // 策略1: 使用公共图片代理服务
    const proxyServices = [
      `https://images.weserv.nl/?url=${encodeURIComponent(originalUrl)}`,
      `https://cors-anywhere.herokuapp.com/${originalUrl}`,
      `https://api.allorigins.win/raw?url=${encodeURIComponent(originalUrl)}`,
    ]

    // 返回第一个代理服务URL
    return proxyServices[0]
  }

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    console.log("[v0] Image load failed, trying fallback")
    setImageError(true)
    setLoading(false)
    if (onError) {
      onError(e)
    }
  }

  const handleImageLoad = () => {
    console.log("[v0] Image loaded successfully")
    setLoading(false)
    setImageError(false)
  }

  if (imageError) {
    return (
      <div className={`bg-muted flex items-center justify-center ${className}`}>
        <div className="text-center p-4">
          <div className="text-muted-foreground text-sm">图片加载失败</div>
          <div className="text-xs text-muted-foreground mt-1">无法显示海报</div>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      {loading && (
        <div className="absolute inset-0 bg-muted flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-primary border-t-transparent"></div>
        </div>
      )}
      <img
        src={getProxiedUrl(src) || "/placeholder.svg"}
        alt={alt}
        className={`w-full h-full object-cover transition-transform group-hover:scale-105 ${loading ? "opacity-0" : "opacity-100"}`}
        onError={handleImageError}
        onLoad={handleImageLoad}
        referrerPolicy="no-referrer"
        crossOrigin="anonymous"
      />
    </div>
  )
}
