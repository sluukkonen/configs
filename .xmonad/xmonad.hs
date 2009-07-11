-- Xmonad settings by sluukkonen (sluukkonen@github)
-- Last update: Sat May 16 13:04:40 EEST 2009

import XMonad
import XMonad.Config.Gnome
import XMonad.Layout.NoBorders

main = xmonad $ gnomeConfig 
		{ 
			-- modMask = mod4Mask,
			terminal = "urxvtc",
			layoutHook = smartBorders $ layoutHook gnomeConfig
		}
