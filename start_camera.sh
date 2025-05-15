#!/bin/sh
# this script starts scrcpy
# it's optimized for my phone using open camera from gplay
# you might need to change v4l2 device

# size of playback video
max_size=480
# x,y of window created by ffplay
window_x=$((1920-max_size))
window_y=$((1080-max_size))
# your v4l2 device
v4l2_device="/dev/video0"

# start scrcpy in backgroud, redirect stdout to /dev/null
scrcpy \
  --video-codec=h264 \
  --video-encoder=OMX.qcom.video.encoder.avc \
  --capture-orientation=0 \
  --crop=1080:1080:0:600 \
  --max-size=$max_size \
  --v4l2-sink=$v4l2_device \
  --no-video-playback \
 > /dev/null &

scrcpy_pid=$!

cleanup() {
  echo "stopping scrcpy and ffplay..."
  kill "$scrcpy_pid" 2>/dev/null
  kill "$ffplay_pid" 2>/dev/null
  wait "$scrcpy_pid" 2>/dev/null
  wait "$ffplay_pid" 2>/dev/null
  exit
}

trap cleanup INT TERM

# wait for scrcpy to start streaming
#while ! ffmpeg -f v4l2 -i "$v4l_device" -frames:v 1 -f null - > /dev/null 2>&1; do
#  sleep 0.1
#done
sleep 5

# now we cam start ffplay
ffplay \
  -noborder \
  -left $window_x \
  -top $window_y \
  -i "$v4l2_device" \
 > /dev/null &

ffplay_pid=$!

# wait for both processes to finish

wait "$scrcpy_pid" "$ffplay_pid"

#ffplay -i $v4l2_device
