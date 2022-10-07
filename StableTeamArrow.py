from arena import *
from time import sleep
import random
import asyncio
from math import *
from scipy.spatial.transform import Rotation as R
def end_program_callback(scene: Scene):
    global sceneParent
    scoreTextID = 0
    # print("cancelling")
    scene.delete_object(sceneParent)
def msg_handler(scene, obj, msg):
    # with open("Log.txt", "a") as file:
    #     file.write(str(msg))
    pass
cameras = {}
players = {}
scoreTextID = 0
class Player():
    def __init__(self, camera):
        global scoreTextID, targetParent
        self.score = 0
        self.camera = camera
        self.id = camera.object_id
        self.name = camera.displayName
        self.color = camera.data.color
        self.scoreText = Text(persist=True, object_id = f"scoreText{scoreTextID}", scale = (1.5, 1.5, 1.5), parent=targetParent, color=self.color)
        scoreTextID += 1
        self.arrowShaftColor = scaleColor(0.2, camera.data.color)
        self.arrowHeadColor = camera.data.color
        self.arrows = []
    def reloadScore(self):
        global scene
        self.scoreText.data.value = f"{self.name}: {self.score}"
        scene.update_object(self.scoreText)
def user_join_callback(scene, camera, msg):
    global players
    cameras[camera.object_id] = camera
    for player in players.values():
        for arrow in player.arrows:
            print(arrow.data.position)
            scene.update_object(arrow)
    # print(camera.data.color)
def user_left_callback(scene, camera, msg):
    # global player_to_score
    global players
    cameraID = camera.object_id
    del cameras[cameraID]
    if cameraID in players.keys():
        player = players[cameraID]
        remove_player(player)

arrow_id = 0
arrow_velocity = 20
arrows_flying = 0
target_rotating = False
sceneParent = Box()
targetParent = Box()
target = Cylinder()
scene = Scene(
    host="mqtt.arenaxr.org",
    scene="teamArchery",
    end_program_callback=end_program_callback,
    user_join_callback=user_join_callback,
    user_left_callback=user_left_callback,
    on_msg_callback=msg_handler
)
def dot(x, y):
    return x[0] * y[0] + x[1] * y[1] + x[2] * y[2]
def scale(s, v):
    return (s*v[0], s*v[1], s*v[2])
def add(x, y):
    return (x[0] + y[0], x[1] + y[1], x[2] + y[2])

#plane: n*p = s, line: p = vt + a
def plane_line_intersect(n, s, v, a):
    t = (s - dot(n, a))/dot(n, v)
    return add(scale(t, v), a)
targetCenter = (0, 1.5, -3.75)
target_normal = (0, 0, -1)
target_s = dot((0, 0, -1), targetCenter)
scoreLocation = (0, 3.5, 0)
radius = 1.5
def distance(p1, p2):
    x = p1[0] - p2[0]
    y = p1[1] - p2[1]
    z = p1[2] - p2[2]
    return (x**2 + y**2 + z**2)**0.5

def rotateColor(color, angle):
    a = angle * pi/180
    x = color.red
    y = color.green
    s = sin(a)
    c = cos(a)
    newRed = c * x - s * y
    newGreen = s * x + c * y
    return Color(int(newRed), int(newGreen), color.blue)
def make_arrow(position, rotation, shaftColor, headColor):
    global arrow_id, sceneParent
    # The "handle" of the arrow is the top cone, its tip, which is the parent of all other components.
    topCone = Cone(
        persist = True,
        object_id = f"XarrowTip{arrow_id}",
        position = position,
        height = 1/3,
        radiusTop = 0,
        radiusBottom = 0.1,
        color = headColor,
        rotation = rotation,
        parent = targetParent
    )
    scene.add_object(topCone)
    bottomCone = Cone(
        persist = True,
        position = (0,-4/3,0),
        object_id = f"YarrowBottom{arrow_id}",
        color = headColor,
        height = 0.2,
        radiusTop = 0,
        radiusBottom = 0.1,
        parent = topCone
    )
    scene.add_object(bottomCone)
    shaft = Cylinder(
        persist = True,
        position = (0, -2/3, 0),
        height = 4/3,
        radius = 0.1/3,
        parent = topCone,
        object_id = f"ZarrowShaft{arrow_id}",
        color = shaftColor
    )
    scene.add_object(shaft)
    arrow_id += 1
    return topCone

def rotation_from_vector(dX, dY, dZ):
    #returns a rotation from (0, 1, 0) to the given vector
    #mainly to orient the arrow (which is normally vertical)
    #a 3d rotation only needs two axis rotations; X and Z are arbitrary axes
    thetaZ = asin(-1 * dX)
    thetaX = acos(dY/(1 - dX**2)**0.5)
    if abs(sin(thetaX)*cos(thetaZ) - dZ) > 0.05:
        thetaZ = pi - thetaZ
        thetaX = pi - thetaX
    return (thetaX * 180/pi, 0, thetaZ * 180/pi)
def reloadPlayerScore(player):
    global scene
    # print(player.scoreText.data)
    player.scoreText.data.value = f"{player.name}: {player.score}"
    scene.update_object(player.scoreText)
    # print(player.scoreText.data)
def update_score(distance, player):
    global players
    player.score += max(0, int((1 - distance / radius) * 5 + 1))
    # reloadPlayerScore(player)
    player.reloadScore()
def reloadScoreText():
    # print("Reloading")
    global players
    spacing = 0.5
    x = scoreLocation[0]
    y = scoreLocation[1]
    z = scoreLocation[2]
    for player in players.values():
        # print("Position:", position)
        playerText = player.scoreText
        playerText.data.position = Position(x, y, z)
        scene.update_object(playerText)
        # print(playerText.data)
        y += spacing

async def animate_arrow(start, end, arrow, time, player, expire=False):
    global arrows_flying
    arrows_flying += 1
    center = (target.data.position.x, target.data.position.y, target.data.position.z + 0.25)
    distanceFromCenter = distance(end, center)
    arrow.dispatch_animation(
        Animation(
            property = "position",
            start = start,
            end = end,
            easing = "linear",
            dur = time
        )
    )
    scene.run_animations(arrow)
    #to sync the score update with the arrow hitting the target
    await scene.sleep(time)
    arrows_flying -= 1
    if expire:
        scene.delete_object(arrow)
    else:
        update_score(distanceFromCenter, player)
        arrow.data.position = Position(end[0], end[1], end[2])
        # print("End:", end)
        # await scene.sleep(50)
        # scene.update_object(arrow)
        print("Position:", arrow.data.position, "Rotation:", arrow.data.rotation)
def scaleColor(s, color):
    return Color(int(s * color.red), int(s * color.green), int(s * color.blue))
def make_box(start, rotation):
    global sceneParent
    box = Box(position=start, depth=3, height=0.5, width=0.5, rotation=rotation, parent=sceneParent)
    scene.add_object(box)
    return box

def worldCoordsToTarget(world):
    global targetParent
    # print(targetParent.data.rotation)
    theta = targetParent.data.rotation.y * pi/180
    targetPosition = (targetParent.data.position.x, targetParent.data.position.y, targetParent.data.position.z)
    shift = scale(-1.0, targetPosition)
    newWorld1 = add(world, shift)
    x = newWorld1[0]
    y = newWorld1[2]
    newWorld2 = (cos(theta) * x - sin(theta) * y, world[1], sin(theta) * x + cos(theta) * y)
    return newWorld2
def target_handler(scene, evt, msg):
    global arrow_velocity, target_s, target_normal, players, targetParent, target_rotating
    if evt.type == "mouseup":
        cameraID = evt.data.source
        if not cameraID in players.keys() or target_rotating:
            return
        player = players[cameraID]
        camera = player.camera
        alignArrow = R.from_euler('x', -90, degrees=True)
        rot = R.from_quat((camera.data.rotation.x, camera.data.rotation.y, camera.data.rotation.z, camera.data.rotation.w))
        v = rot.apply((0, 0, -1))
        # rotation = rotation_from_vector(v[0], v[1], v[2])
        degrees = targetParent.data.rotation.y
        targetRotate = R.from_euler('y', -degrees, degrees=True)
        rot2 = (targetRotate * rot * alignArrow).as_quat()
        rotation = Rotation(rot2[0], rot2[1], rot2[2], rot2[3])
        wStart = (evt.data.clickPos.x, evt.data.clickPos.y, evt.data.clickPos.z)
        tStart = worldCoordsToTarget(wStart)
        # tStart = (evt.data.clickPos.x, evt.data.clickPos.y, evt.data.clickPos.z + 4)
        # print(start)
        # start = worldCoordsToTarget(start)
        # print(target_normal)
        wEnd = plane_line_intersect(target_normal, target_s, v, wStart)
        tEnd = worldCoordsToTarget(wEnd)
        # end = add(plane_line_intersect(target_normal, target_s, v, wStart), (0, 0, 4))
        dX = tEnd[0] - tStart[0]
        dY = tEnd[1] - tStart[1]
        dZ = tEnd[2] - tStart[2]
        magnitude = (dX**2 + dY**2 + dZ**2)**0.5
        arrow = make_arrow(tStart, rotation, player.arrowHeadColor, player.arrowShaftColor)
        time = magnitude / arrow_velocity * 1000
        # print("HI4")
        #animate the arrow flying from the camera to the target
        distanceFromCenter = distance(tEnd, worldCoordsToTarget(targetCenter))
        # distanceFromCenter = 1
        if distanceFromCenter > radius:
            wEnd = add(wEnd, scale(4*arrow_velocity, (v[0], v[1], v[2])))
            scene.event_loop.loop.create_task(
                animate_arrow(tStart, worldCoordsToTarget(wEnd), arrow, time + 4000, player, True)
            )
            print("Expiring")
        else:
            player.arrows.append(arrow)
            scene.event_loop.loop.create_task(animate_arrow(tStart, tEnd, arrow, time, player))
def reset_handler(s, evt, msg):
    global scene, player_to_score, players
    cameraID = evt.data.source
    if not cameraID in players.keys():
        return
    player = players[cameraID]
    player.score = 0
    player.reloadScore()
    for arrow in player.arrows:
        scene.delete_object(arrow)
    player.arrows = []
def rotate_handler(s, evt, msg):
    global scene, sceneParent, players, cameras, target_normal, target_s, targetParent, arrows_flying, target_rotating
    cameraID = evt.data.source
    if not cameraID in players.keys() or arrows_flying != 0:
        return
    camera = cameras[cameraID]
    tPos = targetParent.data.position
    cPos = camera.data.position
    x = cPos.x - tPos.x
    y = cPos.z - tPos.z
    angle = atan2(x, y)
    oldRot = targetParent.data.rotation.y * pi / 180
    rot = angle
    rotation = Rotation(0, angle * 180/pi, 0)
    difference = rot - oldRot
    if difference < 0:
        difference += 2 * pi
    if difference > pi:
        difference = 2 * pi - difference
    print(difference)
    time = (difference / pi) * 1000 * 2
    # print("Hi1")
    # print("Time:", time)
    print(targetParent.data.rotation)
    target_rotating = True
    targetParent.dispatch_animation(
        Animation(
            property = "rotation.y",
            start = targetParent.data.rotation.y,
            end = rotation.y,
            easing = "linear",
            dur = time
        )
    )
    scene.run_animations(targetParent)
    # print("y:", rotation.y)
    targetParent.data.rotation.y = rotation.y
    # print("Hi2")
    target_normal = (sin(angle), 0, cos(angle))
    #the "center" of the target is not constant since it is on the surface of the target while the target rotates about its true center
    centerOffset = scale(0.25, target_normal)
    targetCenter = add((0, 1.5, -4.0), centerOffset)
    target_s = dot(target_normal, targetCenter)
    scene.update_object(targetParent)
    scene.event_loop.loop.create_task(targetNotRotatingAfter(time))
async def targetNotRotatingAfter(time):
    global scene, target_rotating
    await scene.sleep(time)
    target_rotating = False
    # print("done")
def join_handler(s, evt, msg):
    global players, cameras
    cameraID = evt.data.source
    if cameraID in players.keys():
        return
    player = Player(cameras[cameraID])
    players[cameraID] = player
    scene.add_object(player.scoreText)
    player.reloadScore()
    reloadScoreText()
def leave_handler(s, evt, msg):
    global players
    cameraID = evt.data.source
    if not cameraID in players.keys():
        return
    player = players[cameraID]
    remove_player(player)
def remove_player(player):
    global players
    cameraID = player.id
    for arrow in player.arrows:
        scene.delete_object(arrow)
    scene.delete_object(player.scoreText)
    del players[cameraID]
    reloadScoreText()
def make_target(x, z):
    global targetParent, scene, radius, target
    target = Cylinder(
        persist=True,
        object_id="BAtarget",
        position=(x, radius, z),
        height=0.5,
        radius=radius,
        rotation=(90, 0, 0),
        color=(86, 48, 0),
        parent=targetParent
    )
    circle1 = Circle(
        object_id="target1",
        persist=True,
        position=(0,0.26,0),
        radius=radius,
        color=(255,255,255),
        rotation=(-90, 0, 0),
        parent=target
    )
    circle2 = Circle(
        object_id="target2",
        persist=True,
        position=(0,0.27,0),
        radius=radius*4/5,
        color=(0,0,0),
        rotation=(-90, 0, 0),
        parent=target
    )
    circle3 = Circle(
        object_id="target3",
        persist=True,
        position=(0,0.28,0),
        radius=radius*3/5,
        color=(0,0,255),
        rotation=(-90, 0, 0),
        parent=target
    )
    circle4 = Circle(
        object_id="target4",
        persist=True,
        position=(0,0.29,0),
        radius=radius*2/5,
        color=(255,0,0),
        rotation=(-90, 0, 0),
        parent=target
    )
    circle5 = Circle(
        object_id="target5",
        persist=True,
        position=(0,0.30,0),
        radius=radius*1/5,
        color=(255,255,0),
        rotation=(-90, 0, 0),
        parent=target
    )
    #top transparent circle for click events; iOS click events don't seem to work with 2d objects
    clicker = Cylinder(
        persist=True,
        object_id="target6",
        position=(0, 0.2, 0),
        height=0.5,
        radius=radius,
        material=Material(transparent=True, opacity=0),
        parent=target
    )
    scene.add_object(target)
    scene.add_object(circle1)
    scene.add_object(circle2)
    scene.add_object(circle3)
    scene.add_object(circle4)
    scene.add_object(circle5)
    scene.add_object(clicker)
    # scene.update_object(clicker, click_listener=True, evt_handler=target_handler)
    scene.update_object(target, click_listener=True, evt_handler=target_handler)

    return target

def make_button(position, color, text, action):
    global sceneParent, scene, targetParent
    button=Box(persist=True, object_id=f"CButton{text}")
    def callback(s, evt, msg):
        #higlight effect
        if evt.type == "mousedown":
            c = Color(*color)
            button.data.color = scaleColor(1.5, c)
            scene.update_object(button)
        if evt.type == "mouseup":
            button.data.color = Color(color[0], color[1], color[2])
            scene.update_object(button)
            action(s, evt, msg)

    button = Box(
        object_id=f"CButton{text}",
        persist=True,
        position=position,
        width=1,
        height=0.5,
        depth=0.5,
        color=color,
        rotation=(0, 0, 0),
        parent=targetParent.object_id,
        evt_handler=callback,
        click_listener=True
        # parent=sceneParent
    )

    # button.data.click_listener=True
    # button.evt_handler=callback
    scene.add_object(button)
    # scene.update_object(button)
    text = Text(object_id=f"Z{text}", persist=True, position=(0, 0, 0.26), rotation=(0, 0, 0), value=text, color=(0, 0, 0), parent=button.object_id)
    scene.add_object(text)

    # scene.update_object(button, click_listener=True, evt_handler=callback)

def makePlane(depth):
    global scene, sceneParent, target
    plane = Plane(
        id="targetPlane",
        position=(0, 0, -48.5),
        height=100, width=100,
        parent=target,
        rotation=(-90, 0, 0),
        color=(100, 100, 0),
        material=Material(transparent=True, opacity=0)
    )
    scene.add_object(plane)
    scene.update_object(plane, click_listener=True, evt_handler=target_handler)
@scene.run_once
def start():
    # print("Running start")
    global sceneParent, target, targetParent
    # anchor = scene.get_persisted_obj("ARAnchor") Probably not needed at this point
    # arMarker = {'markerid':1, 'markertype':'apriltag_36h11', 'size':100}
    # anchor = Box(persist=True, object_id="ARAnchor", position=(0, 0, 0), armarker=arMarker, scale=(0.25, 0.25, 0.25), rotation=(0, 0, 0))
    # scene.add_object(anchor)
    sceneParent = Box(
        persist=True,
        object_id="AsceneParent",
        position=(0, 0, 0),
        rotation=(0, 0, 0),
        material=Material(transparent=True, opacity=0),
        # parent = anchor
    )
    targetParent = Box(
        persist=True,
        object_id="BTargetParent",
        position=(0, 0, -4),
        rotation=(0, 0, 0),
        color=(100, 0, 0),
        material=Material(transparent=True, opacity=0),
        parent=sceneParent
    )
    scene.add_object(sceneParent)
    scene.add_object(targetParent)

    make_button(( 2.5, 1.2, 0), (150, 100, 0), "Reset", reset_handler)
    make_button(( 2.5, 1.8, 0), (0, 0, 150), "Rotate", rotate_handler)
    make_button((-2.5, 1.2, 0), (150, 0, 0), "Leave", leave_handler)
    make_button((-2.5, 1.8, 0), (0, 150, 10), "Join", join_handler)
    target = make_target(0, 0)
    # make_button(( 2.5, 0, -0.3), (150, 100, 0), "Reset", reset_handler)
    # make_button(( 2.5, 0, 0.3), (0, 0, 150), "Rotate", rotate_handler)
    # make_button((-2.5, 0, -0.3), (150, 0, 0), "Leave", leave_handler)
    # make_button((-2.5, 0, 0.3), (0, 150, 10), "Join", join_handler)
    makePlane(-5)


scene.run_tasks()
