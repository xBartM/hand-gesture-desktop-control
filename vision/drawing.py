import cv2
import mediapipe as mp
import numpy as np
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2

# Type alias for MediaPipe's hand landmarker result
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult

# Constants for drawing
_MARGIN = 10  # Pixels
_FONT_SIZE = 1.0  # OpenCV font scale
_FONT_THICKNESS = 1 # OpenCV font thickness
# Color for handedness text (Green in RGB, as drawing occurs on an RGB image)
_HANDEDNESS_TEXT_COLOR_RGB = (88, 205, 54)


def draw_landmarks_on_image(
    rgb_image: np.ndarray,
    detection_result: HandLandmarkerResult
) -> np.ndarray:
    """Draws hand landmarks and handedness on the input image.

    This function modifies the input `rgb_image` by drawing landmarks and
    text onto it. It's based on MediaPipe's official examples:
    https://colab.research.google.com/github/googlesamples/mediapipe/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb

    Args:
        rgb_image: The input image in RGB format as a NumPy array.
                   This image will be modified.
        detection_result: The result object from MediaPipe HandLandmarker,
                          containing hand_landmarks and handedness.

    Returns:
        The input `rgb_image` NumPy array, now with landmarks and
        handedness drawn on it.
    """
    annotated_image = np.copy(rgb_image) # Work on a copy

    if not detection_result.hand_landmarks:
        return annotated_image # Return copy if no landmarks

    image_height, image_width, _ = annotated_image.shape

    for i, hand_landmarks in enumerate(detection_result.hand_landmarks):
        # Draw the hand landmarks.
        hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
        hand_landmarks_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(
                x=landmark.x, y=landmark.y, z=landmark.z
            ) for landmark in hand_landmarks
        ])
        solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=hand_landmarks_proto,
            connections=solutions.hands.HAND_CONNECTIONS,
            landmark_drawing_spec=solutions.drawing_styles.get_default_hand_landmarks_style(),
            connection_drawing_spec=solutions.drawing_styles.get_default_hand_connections_style()
        )

        # Draw handedness (left or right hand) on the image.
        if detection_result.handedness and i < len(detection_result.handedness):
            handedness_entry = detection_result.handedness[i]
            
            # Calculate text position based on bounding box of landmarks
            x_coords = [landmark.x * image_width for landmark in hand_landmarks]
            y_coords = [landmark.y * image_height for landmark in hand_landmarks]
            
            text_x = int(min(x_coords))
            text_y = int(min(y_coords)) - _MARGIN
            
            # Adjust text position to be within image boundaries
            text_x = max(_MARGIN, text_x)
            # Position text above the hand; ensure it's visible if hand is at top
            text_y = max(_MARGIN * 2, text_y) 

            cv2.putText(
                img=annotated_image,
                text=f"{handedness_entry[0].category_name}",
                org=(text_x, text_y),
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=_FONT_SIZE,
                color=_HANDEDNESS_TEXT_COLOR_RGB,
                thickness=_FONT_THICKNESS,
                lineType=cv2.LINE_AA
            )

    return annotated_image