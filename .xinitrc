# programs to start when X is launched...
urxvtd -q -f -o
gnome-settings-daemon  & 
nautilus --no-desktop &
# fix keyboard issues and map caps lock to ctrl
setxkbmap -option apple:badmap
xmodmap /home/saku/.xmodmap

# Start dbus.
if which dbus-launch >/dev/null && test -z "$DBUS_SESSION_BUS_ADDRESS"; then
       eval `dbus-launch --sh-syntax --exit-with-session`
fi

wmii
