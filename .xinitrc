# programs to start when X is launched...
urxvtd -q -f -o
xfce-mcs-manager  & 
thunar --daemon &
# fix keyboard issues and map caps lock to ctrl
setxkbmap -option apple:badmap
xmodmap /home/saku/.xmodmap

awesome
