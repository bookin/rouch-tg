import * as React from "react"

import {cn} from "@/lib/utils"

const Textarea = React.forwardRef<
	HTMLTextAreaElement,
	React.ComponentProps<"textarea">
>(({className, ...props}, ref) => {
	return (
		<textarea
			className={cn(
				// "flex min-h-[80px] w-full rounded-md form-element-text border border-white/30 bg-white/20 px-3 py-2 shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm backdrop-blur-main hover:bg-white/30 focus:bg-white/80",
				"flex min-h-[80px] w-full rounded-md px-3 py-2 md:text-sm form-element-text form-element-bg",
				className
				)}
			ref={ref}
			{...props}
		/>
	)
})
Textarea.displayName = "Textarea"

export {Textarea}
