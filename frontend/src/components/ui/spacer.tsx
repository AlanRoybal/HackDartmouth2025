import React from "react"

type SpacerProps = {
  axis: "vertical" | "horizontal"
  size: number
}

export const Spacer = ({ size, axis, ...rest }: SpacerProps) => {
  const width = axis === "vertical" ? "1px" : size
  const height = axis === "horizontal" ? "1px" : size

  return (
    <span
      style={{
        display: "block",
        width,
        minWidth: width,
        height,
        minHeight: height,
      }}
      {...rest}
    />
  )
}
