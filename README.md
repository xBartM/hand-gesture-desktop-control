# install scrcpy
# TODO

# for v4l2 using scrcpy
sudo apt install v4l2loopback-dkms
# create v4l2 device - consult scrcpy doc/v4l2.md
sudo modprobe v4l2loopback
# check in /dev/video* - probably the last one is the one created 
ls /dev/video*
# start scrcpy
sh start_camera.sh
# preview - N is your camera
ffplay -i /dev/videoN

# install Python and setup venv
python3 -m venv .venv --prompt hand-desktop
# get opencv
pip install opencv_python
