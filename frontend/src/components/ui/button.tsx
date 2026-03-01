import * as React from "react"
import {Slot} from "@radix-ui/react-slot"
import {cva, type VariantProps} from "class-variance-authority"

import {cn} from "@/lib/utils"
import {Check} from "lucide-react";

const buttonVariants = cva(
	"cursor-pointer inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
	{
		variants: {
			variant: {
				default:
					"bg-primary text-primary-foreground shadow hover:bg-primary/90",
				destructive:
					"bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
				outline:
					"border border-input  shadow-sm hover:bg-accent hover:text-accent-foreground",
				secondary:
					"bg-secondary/50 text-secondary-foreground shadow-sm hover:bg-secondary/80 backdrop-blur-main border border-white/20",
				ghost: "hover:bg-accent/30 hover:text-white",
				link: "text-primary underline-offset-4 hover:underline",
				glass: "bg-white/20 hover:bg-white/40 border border-white/30 text-white backdrop-blur-md shadow-sm",
				option: "w-full whitespace-normal justify-start p-4 rounded-xl border text-left h-auto bg-white/5 border-white/10 text-white/80 hover:bg-white/10 hover:border-white/30",
			},
			size: {
				default: "h-9 px-4 py-2",
				sm: "h-8 rounded-md px-3 text-xs",
				lg: "h-10 rounded-md px-8",
				icon: "h-9 w-9",
				option: "h-auto p-0",
			},
		},
		defaultVariants: {
			variant: "default",
			size: "default",
		},
	}
)

export interface ButtonProps
	extends React.ButtonHTMLAttributes<HTMLButtonElement>,
		VariantProps<typeof buttonVariants> {
	asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
	({className, variant, size, asChild = false, ...props}, ref) => {
		const Comp = asChild ? Slot : "button"
		return (
			<Comp
				className={cn(buttonVariants({variant, size, className}))}
				ref={ref}
				{...props}
			/>
		)
	}
)
Button.displayName = "Button"

interface ButtonOptionProps extends Omit<ButtonProps, "children"> {
	selected?: boolean
	indicator?: "radio" | "checkbox" | false
	children: React.ReactNode
}

const ButtonOption = React.forwardRef<HTMLButtonElement, ButtonOptionProps>(
	(
		{
			className,
			variant = "option",
			size = "option",
			asChild = false,
			selected = false,
			indicator = "radio",
			children,
			...props
		},
		ref
	) => {
		const Comp = asChild ? Slot : "button"

		return (
			<Comp
				className={cn(
					buttonVariants({variant, size}),
					// состояние selected поверх variant="option"
					selected &&
					(indicator === "radio"
						? "bg-white/20 border-white/20"
						: "bg-white/20 border-white"),
					"flex items-center text-white",
					className
				)}
				ref={ref}
				{...props}
			>
				{indicator === "radio" ? (
					<div
						className={cn(
							"w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0",
							selected ? "border-white" : "border-white/30"
						)}
					>
						{selected && (
							<div className="w-2.5 h-2.5 rounded-full bg-white"/>
						)}
					</div>
				) : indicator === "checkbox" ? (
					<div
						className={cn(
							"w-5 h-5 rounded border flex items-center justify-center shrink-0 transition-colors",
							selected ? "border-white" : "border-white/30"
						)}
					>
						{selected && <Check className="h-3.5 w-3.5"/>}
					</div>
				) : null}

				{children}
			</Comp>
		)
	}
)

ButtonOption.displayName = "ButtonOption"

export {Button, ButtonOption, buttonVariants}
