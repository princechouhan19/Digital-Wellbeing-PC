"use client"
import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Image, { StaticImageData } from "next/image"
import { X, ZoomIn, ZoomOut } from "lucide-react"
import { createPortal } from "react-dom"

interface LightboxProps {
  src: string | StaticImageData
  alt: string
  className?: string
  priority?: boolean
}

export function ImageLightbox({ src, alt, className, priority = false }: LightboxProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isZoomed, setIsZoomed] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false)
        setIsZoomed(false)
      }
    }
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown)
      document.body.style.overflow = "hidden"
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = "unset"
    }
  }, [isOpen])

  return (
    <>
      <div 
        className={`cursor-zoom-in relative group ${className || ""}`}
        onClick={() => setIsOpen(true)}
      >
        <Image 
          src={src} 
          alt={alt} 
          fill
          priority={priority}
          className="object-contain" 
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100 rounded-[inherit]">
          <div className="bg-background/80 backdrop-blur-sm p-3 rounded-full shadow-lg">
            <ZoomIn className="w-5 h-5 text-foreground" />
          </div>
        </div>
      </div>

      {mounted && createPortal(
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 md:p-8 backdrop-blur-sm"
              onClick={() => {
                setIsOpen(false)
                setIsZoomed(false)
              }}
            >
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setIsOpen(false)
                  setIsZoomed(false)
                }}
                className="absolute top-4 right-4 md:top-6 md:right-6 p-3 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors z-50"
                aria-label="Close lightbox"
              >
                <X className="w-6 h-6" />
              </button>
              
              <div className="absolute top-4 left-4 md:top-6 md:left-6 flex gap-2 z-50">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setIsZoomed(!isZoomed)
                  }}
                  className="p-3 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
                  aria-label="Toggle zoom"
                >
                  {isZoomed ? <ZoomOut className="w-6 h-6" /> : <ZoomIn className="w-6 h-6" />}
                </button>
              </div>

              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                transition={{ type: "spring", bounce: 0, duration: 0.3 }}
                className={`relative ${isZoomed ? "w-full h-full items-start" : "w-full h-full max-w-7xl items-center"} flex justify-center overflow-auto`}
                onClick={(e) => e.stopPropagation()}
              >
                <div 
                  className={`relative ${isZoomed ? "w-[200vw] h-[200vh] md:w-[150vw] md:h-[150vh] flex-shrink-0" : "w-full h-full"} ${isZoomed ? "cursor-zoom-out" : "cursor-zoom-in"}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    setIsZoomed(!isZoomed)
                  }}
                >
                  <Image
                    src={src}
                    alt={alt}
                    fill
                    className="object-contain"
                    quality={100}
                    unoptimized={isZoomed}
                  />
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  )
}
