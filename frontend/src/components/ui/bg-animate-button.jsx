import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"
import { motion } from "framer-motion"

import { cn } from "@/lib/utils"

const outerDivVariants = cva("relative inline-block overflow-hidden ", {
  variants: {
    size: {
      sm: "",
      default: "",
      lg: "",
    },
    rounded: {
      full: "rounded-full before:rounded-full",
      xl: "rounded-xl before:rounded-xl",
      "2xl": "rounded-2xl before:rounded-2xl",
      "3xl": "rounded-3xl before:rounded-3xl",
      sm: "rounded-sm before:rounded-sm",
      xs: "rounded-xs before:rounded-xs",
      base: "rounded before:rounded",
    },
  },
  defaultVariants: {
    size: "default",
  },
})

const innerSpanVariants = cva(
  [
    "absolute inset-[-1000%] m-auto block ", // Base styles for positioning and display
  ],
  {
    variants: {
      animation: {
        pulse: "animate-pulse", // Pulsating effect
        "spin-fast": "animate-[spin_2s_linear_infinite]", // Continuous rotation
        "spin-slow": "animate-[spin_8s_linear_infinite]", // Bouncing effect
        spin: "animate-[spin_4s_linear_infinite]", // Bouncing effect
        // Add more animations here
      },
      gradient: {
        sunrise: "text-black font-bold",
        ocean:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#a1c4fd_0%,#c2e9fb_50%,#a1c4fd_100%)] ",
        candy:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#ff9a9e_0%,#fad0c4_50%,#fad0c4_90%,#ff9a9e_100%)] ",
        forest:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#85d797_0%,#1a806b_50%,#85d797_100%)] ",
        sunset:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#fe5d75_0%,#f5af19_50%,#fe5d75_100%)] ",
        nebula:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#C084FC_0%,#A855F7_25%,#8B5CF6_50%,#A855F7_75%,#C084FC_100%)] ",
        default:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#E2CBFF_0%,#393BB2_50%,#E2CBFF_100%)] ",
        electric:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#00D4FF_0%,#0066CC_50%,#00D4FF_100%)] ",
        lightning:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#60A5FA_0%,#3B82F6_25%,#1D4ED8_50%,#3B82F6_75%,#60A5FA_100%)] ",
        rainbow:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#FF6B6B_0%,#4ECDC4_16%,#45B7D1_32%,#96CEB4_48%,#FFEAA7_64%,#DDA0DD_80%,#FF6B6B_100%)] ",
        gold:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#FFD700_0%,#FFA500_25%,#FF8C00_50%,#FFA500_75%,#FFD700_100%)] ",
        neon:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#00FF00_0%,#00FFFF_25%,#FF00FF_50%,#00FFFF_75%,#00FF00_100%)] ",
        plasma:
          "bg-[conic-gradient(from_90deg_at_50%_50%,#FF0080_0%,#FF8C00_20%,#FFD700_40%,#00FF80_60%,#0080FF_80%,#FF0080_100%)] ",
      },
    },
    compoundVariants: [
      {
        animation: "spin",
        gradient: "sunrise",
        className: "duration-4s ease-linear", // Customizes the animation duration and easing for a specific variant
      },
    ],
    defaultVariants: {
      animation: "spin",
      gradient: "forest",
    },
  }
)

const buttonVariants = cva(
  "relative px-6 py-2 transition-all duration-150 ease-in-out disabled:pointer-events-none disabled:opacity-50 text-sm overflow-hidden",
  {
    variants: {
      size: {
        sm: "text-xs px-4 py-1",
        default: "text-sm px-6 py-2",
        lg: "text-base px-10 py-3 min-w-fit",
      },
      shadow: {
        flat: "",
        soft: "shadow-[0_2px_4px_rgba(0,0,0,0.15),inset_0_1px_1px_rgba(255,255,255,0.15),inset_0_-1px_2px_rgba(0,0,0,0.3)] dark:shadow-[0_2px_4px_rgba(0,0,0,0.25),inset_0_1px_1px_rgba(0,0,0,0.2),inset_0_-1px_2px_rgba(0,0,0,0.5)]",
        base: "shadow-[0_3px_5px_rgba(0,0,0,0.2),inset_0_0.5px_1px_rgba(255,255,255,0.1),inset_0_-2px_3px_rgba(0,0,0,0.4)] dark:shadow-[0_3px_5px_rgba(0,0,0,0.3),inset_0_0.5px_1px_rgba(0,0,0,0.2),inset_0_-2px_3px_rgba(0,0,0,0.6)]",
        deep: "shadow-[0_4px_6px_rgba(0,0,0,0.25),inset_0_1px_2px_rgba(255,255,255,0.2),inset_0_-2px_4px_rgba(0,0,0,0.5)] dark:shadow-[0_4px_6px_rgba(0,0,0,0.35),inset_0_1px_2px_rgba(0,0,0,0.3),inset_0_-2px_4px_rgba(0,0,0,0.7)]",
        deeper:
          "shadow-[0_6px_8px_rgba(0,0,0,0.3),inset_0_2px_3px_rgba(255,255,255,0.25),inset_0_-3px_6px_rgba(0,0,0,0.6)] dark:shadow-[0_6px_8px_rgba(0,0,0,0.4),inset_0_2px_3px_rgba(0,0,0,0.35),inset_0_-3px_6px_rgba(0,0,0,0.8)]",
      },
      gradient: {
        sunrise: "text-black font-bold",
        ocean: "text-black font-bold",
        candy: "text-black font-bold",
        forest: "text-white font-bold",
        sunset: "text-black font-bold",
        nebula: "text-white font-bold",
        default: "text-white font-bold",
        electric: "text-white font-bold",
        lightning: "text-white font-bold",
        rainbow: "text-white font-bold",
        gold: "text-black font-bold",
        neon: "text-black font-bold",
        plasma: "text-white font-bold",
      },
      rounded: {
        full: "rounded-full before:rounded-full",
        xl: "rounded-xl before:rounded-xl",
        "2xl": "rounded-2xl before:rounded-2xl",
        "3xl": "rounded-3xl before:rounded-3xl",
        sm: "rounded-sm before:rounded-sm",
        xs: "rounded-xs before:rounded-xs",
        base: "rounded before:rounded",
      },
    },
    defaultVariants: {
      size: "default",
      shadow: "base",
      rounded: "xl",
    },
  }
)

const BgAnimateButton = React.forwardRef((
  {
    variant = "primary",
    size = "default",
    showBackground = false,
    rounded = "xl",
    shadow = "soft",
    gradient = "electric",
    animation = "spin",
    className,
    asChild = false,
    ...props
  },
  ref
) => {
  const Comp = asChild ? Slot : motion.button

  return (
    <Comp
      className={cn(outerDivVariants({ size, rounded }), className)}
      ref={ref}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
      {...props}
    >
      {gradient && (
        <motion.span 
          className={cn(innerSpanVariants({ gradient, animation }))}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        />
      )}

      <motion.div
        className={cn(buttonVariants({ shadow, rounded, size, gradient }))}
        initial={{ opacity: 0.8 }}
        animate={{ opacity: 1 }}
        whileHover={{ boxShadow: "0 10px 25px rgba(0,0,0,0.2)" }}
        transition={{ duration: 0.2 }}
      >
        {props.children || "Button"}
      </motion.div>
    </Comp>
  )
})

BgAnimateButton.displayName = "BgAnimateButton"

export { BgAnimateButton } 