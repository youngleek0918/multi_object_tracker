from imutils.video import FPS
import argparse
import imutils
import dlib
import time
import cv2
import multiprocessing
import pandas as pd





# this function get called whenever new prosess is created.
# simply update points of each objects.
def start_tracker(box, rgb, inputQueue, outputQueue):
    # print('different processing', color)

    id = box[0]
    startX = box[1][0]
    startY = box[1][1]
    endX = box[1][0]+box[1][2]
    endY = box[1][1]+box[1][3]

    t = dlib.correlation_tracker()
    t.start_track(rgb, dlib.rectangle(startX, startY, endX, endY))
    #print("tracking is started")



    while True:
        rgb = inputQueue.get()

        if rgb is not None:
            t.update(rgb)
            pos = t.get_position()

            # unpack the position object
            startX = int(pos.left())
            startY = int(pos.top())
            endX = int(pos.right())
            endY = int(pos.bottom())


            # add the label + bounding box coordinates to the output
            # queue
            outputQueue.put((id,startX, startY, endX, endY))




data_list = []


# initialize our lists of queues -- both input queue and output queue
# for *every* object that we will be tracking
inputQueues = []
outputQueues = []

boxes = []
colors = []

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", required=True,
                help="path to input video file")
args = vars(ap.parse_args())

print("Show first frame of video for choosing objects")
cap = cv2.VideoCapture(args["video"])

# Read first frame
grabbed, frame = cap.read()
frame = imutils.resize(frame, width=1000)


id = 0

# this loop let users draw the selection boxes
while True:
    boxes.append((id, cv2.selectROI('Trackers', frame, fromCenter=False, showCrosshair=True)))
    id += 1
    k = cv2.waitKey(0) & 0xFF
    if k == 113:  # q is pressed
        break

i = 0

start = time.time()
while True:
    success, frame = cap.read()

    try:
        frame = imutils.resize(frame, width=1000)
    except Exception as e:
        print(str(e))


    if frame is None:
        print("vidde is done")
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    if len(inputQueues) == 0:
        for box in boxes:

            iq = multiprocessing.Queue()
            oq = multiprocessing.Queue()
            inputQueues.append(iq)
            outputQueues.append(oq)

            p = multiprocessing.Process(
                target=start_tracker,
                args=(box, rgb, iq, oq)
            )

            p.daemon = True
            p.start()

            cv2.rectangle(frame, (box[1][0], box[1][1]), (box[1][0]+box[1][2], box[1][1]+box[1][3]),
                          (0, 255, 0), 2)
    else:
        for iq in inputQueues:
            iq.put(rgb)

        for oq in outputQueues:
            # grab the updated bounding box coordinates for the
            # object -- the .get method is a blocking operation so
            # this will pause our execution until the respective
            # process finishes the tracking update
            (object_id, startX, startY, endX, endY) = oq.get()
            end = time.time()

            data_list.append({'id': object_id, 'x': (startX + endX) / 2, 'y': (startY + endY) / 2, 'time': end - start})
            cv2.rectangle(frame, (startX, startY), (endX, endY),
                          (0, 255, 0), 2)

    cv2.imshow('Trackers', frame)
    if cv2.waitKey(1) & 0xFF == 27:  # Esc pressed
        break

#export to csv
data_list = sorted(data_list, key=lambda k: k['id'])
df = pd.DataFrame(data_list, columns=['id', 'x', 'y', 'time'])
df.to_csv('Galaxy7-stationary.csv', encoding='utf-8')

# do a bit of cleanup
cv2.destroyAllWindows()
cap.release()


