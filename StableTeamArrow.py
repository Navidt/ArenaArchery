from arena import *
from time import sleep, time
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
class SceneOptions(Object):
    object_type = "scene-options"
    object_id = "scene-options"
    class Data():
        pass
    class EnvPresets():
        active = True
        preset = "default"
    class Options():
        clickableOnlyEvents = True
        maxAVDist = 20
        privateScene = False
        videoFrustumCulling = True
        videoDistanceConstraints = True
        videoDefaultResolutionConstraint = 180
        physics = False
        pass
    def __init__(self, **kwargs):
        if not "persist" in kwargs:
            self.__dict__["persist"] = False
        else:
            self.__dict__["persist"] = kwargs["persist"]
        if "object_id" in kwargs:
            self.__dict__["object_id"] = kwargs["object_id"]
        self.__dict__["env-presets"] = SceneOptions.EnvPresets()
        self.__dict__["scene-options"] = SceneOptions.Options()
        for property in ["clickableOnlyEvents", "maxAVDist", "privateScene", "videoFrustumCulling", "videoDistanceConstraints", "videoDefaultResolutionConstraint", "physics]"]:
            if property in kwargs:
                self.__dict__["scene-options"][property] = kwargs[property]
        super().__init__(object_type=SceneOptions.object_type, **kwargs)
class Player():
    def __init__(self, camera):
        global scoreTextID, targetParent
        self.score = 0
        self.clickStart = 0.0
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
gravity = -3
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
#plane: n*p = s, parabola: p = (0, 0, a)t^2 + bt + c
def plane_parabola_intersect(n, s, a, b, c):
    print("ABC:", a, b, c)
    t = (s - dot(n, c))/dot(n, b)
    print(t)
    return (t, add(add(scale(t*t, (0, a, 0)), scale(t, b)), c))

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
def arrow_position(start, velocity, t):
    x = t*velocity[0] + start[0]
    y = 0.5*t*t*gravity + t*velocity[1] + start[1]
    z =  t*velocity[2] + start[2]
    return (x, y, z)
async def shoot_arrow(arrow, player, flightTime, start, velocity, expire=False):
    print("TIME:", flightTime)
    print(start, velocity)
    global arrows_flying
    arrows_flying += 1
    center = (target.data.position.x, target.data.position.y, target.data.position.z + 0.25)
    p1 = arrow_position(start, velocity, flightTime*1/3)
    p2 = arrow_position(start, velocity, flightTime*2/3)
    p3 = arrow_position(start, velocity, flightTime)
    print("End:", p3)
    # flightTime *= 10
    print("NEWtime", flightTime)
    distanceFromCenter = distance(p3, center)
    # arrow.dispatch_animation([
    #     Animation(property="position", start=start, end=p1, dur=flightTime/3, easing="linear"),
    #     Animation(property="position", start=p1, end=p2, dur=flightTime/3, easing="linear", delay=flightTime/3),
    #     Animation(property="position", start=p2, end=p3, dur=flightTime/3, easing="linear", delay=flightTime*2/3)
    # ])
    animations = []
    s = 20
    for i in range(s):
        dur = flightTime * 1/s * 1000
        t1 = flightTime * i/s
        t2 = flightTime * (i + 1)/s
        # animations.append(Animation(property="rotation", start=(0, 0, 0), end=(90, 90, 0), dur=dur, easing="linear", delay=t1*1000))
        animations.append(Animation(property="position", start=arrow_position(start, velocity, t1), end=arrow_position(start, velocity, t2), dur=dur, easing="linear", delay=t1*1000))
    # arrow.dispatch_animation([
    #     Animation(property="position", start=start, end=p1, dur=flightTime/3*1000, easing="linear"),
    #     Animation(property="position", start=p1, end=p2, dur=flightTime/3*1000, easing="linear", delay=flightTime/3*1000),
    #     Animation(property="position", start=p2, end=p3, dur=flightTime/3*1000, easing="linear", delay=flightTime*2/3*1000)
    # ])
    arrow.dispatch_animation(animations)
    scene.run_animations(arrow)
    await scene.sleep(flightTime * 1000)
    arrows_flying -= 1
    if expire:
        scene.delete_object(arrow)
    else:
        update_score(distanceFromCenter, player)
        arrow.data.position = Position(p3[0], p3[1], p3[2])
def arrow_hit_target(arrow):
    global arrows_flying, scene
    arrows_flying -= 1
    arrow.data.physics = Physics("none")
    secne.update_object(arrow)
#Try to update individually
#Drop in the middle
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
    cameraID = evt.data.source
    if not cameraID in players.keys() or target_rotating:
        return
    player = players[cameraID]
    if evt.type == "mousedown":
        player.clickStart = time()
    elif evt.type == "mouseup":
        clickDuration = time() - player.clickStart
        arrowSpeed = clickDuration * 10
        if arrowSpeed < 5:
            arrowSpeed = 5
        elif arrowSpeed > 40:
            arrowSpeed = 40
        # arrowSpeed = 20
        print("ARROWSPEED", arrowSpeed)
        camera = player.camera
        alignArrow = R.from_euler('x', -90, degrees=True)
        rot = R.from_quat((camera.data.rotation.x, camera.data.rotation.y, camera.data.rotation.z, camera.data.rotation.w))
        v = rot.apply((0, 0, -1))
        # rotation = rotation_from_vector(v[0], v[1], v[2])
        degrees = targetParent.data.rotation.y
        targetRotate = R.from_euler('y', -degrees, degrees=True)
        rot2 = (targetRotate * rot * alignArrow).as_quat()
        rotation = Rotation(rot2[0], rot2[1], rot2[2], rot2[3])
        #R.from_euler('y', degrees, degrees=True)
        k = (R.from_euler('y', -degrees, degrees=True) * rot).apply((0, 0, -1))
        print("k:", k)
        wStart = (evt.data.clickPos.x, evt.data.clickPos.y, evt.data.clickPos.z)
        tStart = worldCoordsToTarget(wStart)
        # tStart = (evt.data.clickPos.x, evt.data.clickPos.y, evt.data.clickPos.z + 4)
        # print(start)
        # start = worldCoordsToTarget(start)
        # print(target_normal)
        # wEnd = plane_line_intersect(target_normal, target_s, v, wStart)
        velocityW = scale(arrowSpeed, v)
        velocityT = scale(arrowSpeed, k)
        print("velocityW:", velocityW)
        print("velocityT:", velocityT)
        print("Target Normal:", target_normal)
        flightTime, wEnd = plane_parabola_intersect(target_normal, target_s, gravity / 2, velocityW, wStart)
        print("wEND:", wEnd)
        tEnd = worldCoordsToTarget(wEnd)
        """
        dX = tEnd[0] - tStart[0]
        dY = tEnd[1] - tStart[1]
        dZ = tEnd[2] - tStart[2]
        magnitude = (dX**2 + dY**2 + dZ**2)**0.5
        """
        arrow = make_arrow(tStart, rotation, player.arrowHeadColor, player.arrowShaftColor)
        # shoot_arrow(impulse, arrow, player)
        """
        time = magnitude / arrow_velocity * 1000
        """
        # print("HI4")
        #animate the arrow flying from the camera to the target
        distanceFromCenter = distance(tEnd, worldCoordsToTarget(targetCenter))
        print("DISTANCE:", distanceFromCenter)
        if distanceFromCenter > radius:
            """
            wEnd = add(wEnd, scale(4*arrow_velocity, (v[0], v[1], v[2])))
            scene.event_loop.loop.create_task(
                animate_arrow(tStart, worldCoordsToTarget(wEnd), arrow, time + 4000, player, True)
            )
            """
            flightTime += 4
            # scene.event_loop.loop.create_task(
            #     animate_arrow(tStart, worldCoordsToTarget(wEnd), arrow, time + 4000, player, True)
            # )
            scene.event_loop.loop.create_task(
                shoot_arrow(arrow, player, flightTime, tStart, velocityT, True)
            )
            print("Expiring")
        else:
            player.arrows.append(arrow)
            # scene.event_loop.loop.create_task(animate_arrow(tStart, tEnd, arrow, time, player))
            scene.event_loop.loop.create_task(
                shoot_arrow(arrow, player, flightTime, tStart, velocityT)
            )

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
    # sceneOptions = SceneOptions(physics=True)
    # scene.add_object(sceneOptions)
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
