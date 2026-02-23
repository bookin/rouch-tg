// import {Brain} from "lucide-react";
import React from "react";

export default function PageHeader({text, icon}: {text: string, icon: any}) {
  return (
    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3 text-white">
		{React.createElement(icon, {className: "h-8 w-8"})}
	  {/*<Brain className="h-8 w-8 text-primary" />*/}
		{text}
	</h1>
  )
}