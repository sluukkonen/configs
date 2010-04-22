import XMonad
import XMonad.Config.Gnome
import XMonad.Layout.NoBorders
import XMonad.Hooks.ManageHelpers (isFullscreen, doFullFloat)

main = xmonad $ gnomeConfig 
    { 
        terminal   = "gnome-terminal",
        layoutHook = smartBorders $ layoutHook gnomeConfig,
        manageHook = composeAll
            [ manageHook gnomeConfig,
              isFullscreen --> doFullFloat ]
    }
