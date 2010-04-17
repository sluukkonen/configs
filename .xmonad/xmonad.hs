import XMonad
import XMonad.Config.Gnome
import XMonad.Layout.NoBorders

main = xmonad $ gnomeConfig 
		{ 
			terminal = "gnome-terminal",
			layoutHook = smartBorders $ layoutHook gnomeConfig
		}
