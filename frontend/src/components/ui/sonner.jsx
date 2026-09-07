import { useTheme } from "next-themes"
import { Toaster as Sonner } from "sonner";
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"

const Toaster = ({
  ...props
}) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme}
      className="toaster group"
      icons={{
        success: (
          <CircleCheckIcon className="size-4" />
        ),
        info: (
          <InfoIcon className="size-4" />
        ),
        warning: (
          <TriangleAlertIcon className="size-4" />
        ),
        error: (
          <OctagonXIcon className="size-4" />
        ),
        loading: (
          <Loader2Icon className="size-4 animate-spin" />
        ),
      }}
      position="bottom-right"
      style={
        {
          "--normal-bg": "var(--primary-fixed-dim)",
          "--normal-text": "#FFFFFF",
          "--normal-border": "rgba(255,255,255,0.12)",
          "--border-radius": "12px"
        }
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast group-[.toaster]:bg-primary-fixed-dim group-[.toaster]:text-white group-[.toaster]:border-white/10 rounded-xl shadow-lg",
        },
      }}
      {...props} />
  );
}

export { Toaster }
