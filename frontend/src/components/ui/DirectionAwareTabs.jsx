"use client"

import { ReactNode, useMemo, useState } from "react"
import { motion } from "framer-motion"

import { cn } from "@/lib/utils"

function DirectionAwareTabs({
  tabs,
  className,
  rounded,
  onChange,
}) {
  const [activeTab, setActiveTab] = useState(0)
  const [direction, setDirection] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)

  const handleTabClick = (newTabId) => {
    if (newTabId !== activeTab && !isAnimating) {
      const newDirection = newTabId > activeTab ? 1 : -1
      setDirection(newDirection)
      setActiveTab(newTabId)
      onChange ? onChange(newTabId) : null
    }
  }

  const variants = {
    initial: (direction) => ({
      x: 300 * direction,
      opacity: 0,
      filter: "blur(4px)",
    }),
    active: {
      x: 0,
      opacity: 1,
      filter: "blur(0px)",
    },
    exit: (direction) => ({
      x: -300 * direction,
      opacity: 0,
      filter: "blur(4px)",
    }),
  }

  return (
    <div className="flex flex-col items-center w-full">
      <div
        className={cn(
          "flex space-x-0.5 sm:space-x-1 border border-gray-200 dark:border-gray-800 rounded-full cursor-pointer bg-gray-100 dark:bg-gray-900 px-[2px] sm:px-[3px] py-[2px] sm:py-[3.2px] shadow-lg",
          className,
          rounded
        )}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabClick(tab.id)}
            className={cn(
              "relative rounded-full px-2 sm:px-3.5 py-1 sm:py-1.5 text-xs sm:text-sm font-medium transition focus-visible:outline-1 focus-visible:ring-1 focus-visible:outline-none flex gap-1 sm:gap-2 items-center whitespace-nowrap",
              activeTab === tab.id
                ? "text-white dark:text-gray-900"
                : "hover:text-gray-600 dark:hover:text-gray-400 text-gray-500 dark:text-gray-500",
              rounded
            )}
            style={{ WebkitTapHighlightColor: "transparent" }}
          >
            {activeTab === tab.id && (
              <motion.span
                layoutId="bubble"
                className="absolute inset-0 z-10 bg-gray-900 dark:bg-gray-100 shadow-lg border border-gray-300 dark:border-gray-700"
                style={rounded ? { borderRadius: 9 } : { borderRadius: 9999 }}
                transition={{ type: "spring", bounce: 0.19, duration: 0.4 }}
              />
            )}

            <span className="relative z-20">{tab.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
export { DirectionAwareTabs } 