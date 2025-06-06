"use client"

import { useEffect } from "react"
import { motion, useSpring, useTransform } from "framer-motion"

export function AnimatedNumber({
  value,
  mass = 0.8,
  stiffness = 75,
  damping = 15,
  precision = 0,
  format = (num) => num.toLocaleString(),
  onAnimationStart,
  onAnimationComplete,
  className,
}) {
  const spring = useSpring(parseFloat(value) || 0, { mass, stiffness, damping })
  const display = useTransform(spring, (current) => {
    const numericValue = parseFloat(current) || 0;
    return format(parseFloat(numericValue.toFixed(precision)));
  })

  useEffect(() => {
    const numericValue = parseFloat(value) || 0;
    spring.set(numericValue)
    if (onAnimationStart) onAnimationStart()
    const unsubscribe = spring.on("change", () => {
      if (Math.abs(spring.get() - numericValue) < 0.01 && onAnimationComplete) {
        onAnimationComplete()
      }
    })
    return () => unsubscribe()
  }, [spring, value, onAnimationStart, onAnimationComplete])

  return <motion.span className={className}>{display}</motion.span>
}

export function AnimatedPercentage({
  value,
  mass = 0.8,
  stiffness = 75,
  damping = 15,
  precision = 1,
  className,
  onAnimationStart,
  onAnimationComplete,
}) {
  const spring = useSpring(parseFloat(value) || 0, { mass, stiffness, damping })
  const display = useTransform(spring, (current) => {
    const numericValue = parseFloat(current) || 0;
    return `${numericValue.toFixed(precision)}%`;
  })

  useEffect(() => {
    const numericValue = parseFloat(value) || 0;
    spring.set(numericValue)
    if (onAnimationStart) onAnimationStart()
    const unsubscribe = spring.on("change", () => {
      if (Math.abs(spring.get() - numericValue) < 0.01 && onAnimationComplete) {
        onAnimationComplete()
      }
    })
    return () => unsubscribe()
  }, [spring, value, onAnimationStart, onAnimationComplete])

  return <motion.span className={className}>{display}</motion.span>
} 